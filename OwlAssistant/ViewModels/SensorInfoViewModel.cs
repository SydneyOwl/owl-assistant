using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.Reactive;
using System.Reactive.Disposables;
using System.Reactive.Linq;
using System.Threading.Tasks;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Controls.Notifications;
using Avalonia.Styling;
using DynamicData;
using Flurl.Http;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using OwlAssistant.Resources;
using ReactiveUI;
using ReactiveUI.Fody.Helpers;
using ScottPlot;
using ScottPlot.Avalonia;
using ScottPlot.PlotStyles;
using Serilog;
using Notification = Avalonia.Controls.Notifications.Notification;

namespace OwlAssistant.ViewModels;

public class SensorInfoViewModel : ViewModelBase
{
    public ReactiveCommand<Unit, Unit> RefreshSensor { get; }
    public ReactiveCommand<Unit, Unit> RefreshChart { get; }
    public ReactiveCommand<Unit, Unit> RefreshAll { get; }
    
    private bool _inited; 

    public SensorInfoViewModel()
    {
        RefreshSensor = ReactiveCommand.CreateFromTask(_getSensorInfo);
        RefreshChart = ReactiveCommand.CreateFromTask(_refreshChart);
        RefreshAll = ReactiveCommand.CreateFromTask(async () =>
        {
            await _getSensorInfo();
            await _refreshChart();
        });
        
        PlotControl = new AvaPlot();
        if (Application.Current!.ActualThemeVariant == ThemeVariant.Dark) PlotControl.Plot.SetStyle(new Dark());
        else PlotControl.Plot.SetStyle(new Light());
        PlotControl.Refresh();
        
        this.WhenActivated(disposable =>
        {
            RefreshAll.ThrownExceptions.Subscribe(exception =>
            {
                Log.Error("Error occurred: {Exception}", exception);
                GlobalVar.Manager?.Show(new Notification("Error",  exception.Message, NotificationType.Error));
            }).DisposeWith(disposable);
            
            RefreshChart.ThrownExceptions.Subscribe(exception =>
            {
                Log.Error("Error occurred: {Exception}", exception);
                GlobalVar.Manager?.Show(new Notification("Error",  exception.Message, NotificationType.Error));
            }).DisposeWith(disposable);
            
            RefreshSensor.ThrownExceptions.Subscribe(exception =>
            {
                Log.Error("Error occurred: {Exception}", exception);
                GlobalVar.Manager?.Show(new Notification("Error",  exception.Message, NotificationType.Error));
            }).DisposeWith(disposable);
            
            ChartSensor = "outside";

            this.WhenAnyValue(x => x.ChartSensor)
                .Subscribe(sensor =>
                {
                    SensorDataTypeOptions.Clear();
                    SensorDataTypeOptions.AddRange(_sensorDataTypeOptions[ChartSensor]);
                    ChartSensorDataType = SensorDataTypeOptions.First();
                })
                .DisposeWith(disposable);
            
            if (Design.IsDesignMode)return;
            Observable.Interval(TimeSpan.FromSeconds(10))
                .Select(_ => Unit.Default)
                .InvokeCommand(RefreshSensor)
                .DisposeWith(disposable);

            if (!_inited)
            {
                _inited = true;
                Observable.Return(Unit.Default)
                    .InvokeCommand(RefreshAll)
                    .DisposeWith(disposable);
            }
        });
    }

    private async Task _getSensorInfo()
    {
        Log.Debug("Fetching sensor.");
        var result = await GlobalCfg.SensorData
            .WithTimeout(TimeSpan.FromSeconds(GlobalCfg.DefaultRequestTimeout))
            .GetStringAsync();

        var tmp = JsonConvert.DeserializeObject<List<JObject>>(result);
        if (tmp is null) throw new Exception("Invalid data!");
        foreach (var obj in tmp)
        {
            var temperature = obj["temp"]!.ToString();
            var humidity = obj["humi"]!.ToString();
            var battery = obj["batt"]!.ToString();
            var mac = obj["name"]!.ToString();
            var reportTime = obj["time"]!.ToString();
            var reportedTime = DateTimeOffset.FromUnixTimeSeconds(obj["stamp"]!.ToObject<long>()).LocalDateTime;
            
            if (mac == GlobalCfg.InsideSensorMac)
            {
                if (DateTime.Now - reportedTime > TimeSpan.FromMinutes(10))
                {
                    InsideTemperature = "TIMEOUT";
                    InsideHumidity = "TIMEOUT";
                    InsidePower = "TIMEOUT";
                    InsideReportTime = "TIMEOUT";
                    continue;
                }

                InsideTemperature = $"{temperature}°C";
                InsideHumidity =$"{humidity}%";
                InsidePower = $"{battery}%";
                InsideReportTime = $"{reportTime}";
            }
            
            if (mac == GlobalCfg.OutsideSensorMac)
            {
                if (DateTime.Now - reportedTime > TimeSpan.FromMinutes(10))
                {
                    OutsideTemperature = "TIMEOUT";
                    OutsideHumidity = "TIMEOUT";
                    OutsidePower = "TIMEOUT";
                    OutsideReportTime = "TIMEOUT";
                    continue;
                }

                OutsideTemperature = $"{temperature}°C";
                OutsideHumidity =$"{humidity}%";
                OutsidePower = $"{battery}%";
                OutsideReportTime = $"{reportTime}";
            }

        }
    }

    private async Task _refreshChart()
    {
        Log.Debug("Fetching chart");
        try
        {
            PlotControl.Plot.Clear();
        
            var result = await GlobalCfg.SensorDataRange
                .WithTimeout(TimeSpan.FromSeconds(GlobalCfg.DefaultRequestTimeout))
                .PostJsonAsync(new
                {
                    start = $"{ChartStartFrom:yyyy-MM-dd} 00:00:00",
                    end = $"{ChartEndFrom:yyyy-MM-dd} 23:59:59",
                })
                .ReceiveString();

            var tmp = JsonConvert.DeserializeObject<JObject>(result);
            if (tmp is null) throw new Exception("Invalid data!");

            var target = tmp[ChartSensor]?.ToObject<List<JObject>>();
            if(target is null  ||  target.Count == 0) return;

            var xs = target?.Select(x => DateTime.Parse(x["time"]!.ToString().Replace(" GMT", ""))).ToArray();
            var ys = target?.Select(x => double.Parse(x[ChartSensorDataType]!.ToString())).ToArray();
            
            // DateTime[] xs = Generate.ConsecutiveHours(100);
            // double[] ys = Generate.RandomWalk(100);
            var scat = PlotControl.Plot.Add.Scatter(xs, ys);

            var axis = PlotControl.Plot.Axes.DateTimeTicksBottom();
            static string CustomFormatter(DateTime dt)
            {
                bool isMidnight = dt is { Hour: 0, Minute: 0, Second: 0 };
                return isMidnight
                    ? DateOnly.FromDateTime(dt).ToString()
                    : TimeOnly.FromDateTime(dt).ToString();
            }
        
            var tickGen = (ScottPlot.TickGenerators.DateTimeAutomatic)axis.TickGenerator;
            tickGen.LabelFormatter = CustomFormatter;
            PlotControl.Plot.Axes.AutoScale();
            if (Application.Current!.ActualThemeVariant == ThemeVariant.Dark) PlotControl.Plot.SetStyle(new Dark());
            else PlotControl.Plot.SetStyle(new Light());
        }
        finally
        {
            PlotControl.Refresh();
        }
    }

    private void _resetInsideValue()
    {
        InsideTemperature = "?";
        InsideHumidity = "?";
        InsidePower = "?";
        InsideReportTime = "?";
    }
    
    private void _resetOutsideValue()
    {
        OutsideTemperature = "?";
        OutsideHumidity = "?";
        OutsidePower = "?";
        OutsideReportTime = "?";
    }

    private void _resetValue()
    {
        _resetInsideValue();
        _resetOutsideValue();
    }
    
    [Reactive] public string InsideTemperature { get; set; } = "?";
    [Reactive] public string InsideHumidity { get; set; } = "?";
    [Reactive] public string InsidePower { get; set; } = "?";
    [Reactive] public string InsideReportTime { get; set; } = "?";
    [Reactive] public string OutsideTemperature { get; set; } = "?";
    [Reactive] public string OutsideHumidity { get; set; } = "?";
    [Reactive] public string OutsidePower { get; set; } = "?";
    [Reactive] public string OutsideReportTime { get; set; } = "?";
    [Reactive] public DateTime ChartStartFrom { get; set; } = DateTime.Now;
    [Reactive] public DateTime ChartEndFrom { get; set; } = DateTime.Now;
    [Reactive] public string ChartSensor { get; set; }
    [Reactive] public string ChartSensorDataType { get; set; }

    public ObservableCollection<string> SensorDataTypeOptions { get; set; } = new();
    
    public List<string> SensorOptions { get; } = ["inside", "outside"];
    private Dictionary<string, List<string>> _sensorDataTypeOptions { get; } = new()
    {
        ["inside"] = ["temp", "humi"],
        ["outside"] = ["temp", "humi"],
    };
    
    public AvaPlot PlotControl { get; private set; }
}