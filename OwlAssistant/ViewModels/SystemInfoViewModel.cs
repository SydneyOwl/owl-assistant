using System;
using System.Reactive;
using System.Reactive.Disposables;
using System.Reactive.Linq;
using System.Runtime.InteropServices;
using System.Threading.Tasks;
using Avalonia.Controls;
using Avalonia.Controls.Notifications;
using Flurl.Http;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using OwlAssistant.Resources;
using ReactiveUI;
using ReactiveUI.Fody.Helpers;
using Notification = Avalonia.Controls.Notifications.Notification;

namespace OwlAssistant.ViewModels;

public class SystemInfoViewModel : ViewModelBase
{
    [Reactive] public string? SystemInfo { get; set; } = "PRESS REFRESH";

    [Reactive] public string CpuUtilization { get; set; } = "?";
    [Reactive] public string CpuTemp { get; set; } = "?";
    [Reactive] public string MemUtilization { get; set; } = "?";
    [Reactive] public string SysLoad { get; set; } = "?";
    
    
    public ReactiveCommand<Unit, Unit> RefreshAllCommand { get; set; }
    private ReactiveCommand<Unit, Unit> RefreshTextCommand { get; set; }
    private ReactiveCommand<Unit, Unit> RawRefreshCommand { get; set; }
    public ReactiveCommand<Unit, Unit> SysPrintCommand { get; set; }

    private bool _inited; 

    public SystemInfoViewModel()
    {
        RefreshAllCommand = ReactiveCommand.CreateFromTask(async ()=>
        {
            await _doTextRefresh();
            await _doRawRefresh();
        });
        RefreshTextCommand = ReactiveCommand.CreateFromTask(_doTextRefresh);
        RawRefreshCommand = ReactiveCommand.CreateFromTask(_doRawRefresh);
        SysPrintCommand = ReactiveCommand.CreateFromTask(_doPrintSysInfo);
        
        this.WhenActivated(disposable =>
        {
            RefreshAllCommand.ThrownExceptions.Subscribe(exception =>
            {
                GlobalVar.Manager?.Show(new Notification("Error",  exception.Message, NotificationType.Error));
            }).DisposeWith(disposable);
            
            RefreshTextCommand.ThrownExceptions.Subscribe(exception =>
            {
                GlobalVar.Manager?.Show(new Notification("Error",  exception.Message, NotificationType.Error));
            }).DisposeWith(disposable);
            
            RawRefreshCommand.ThrownExceptions.Subscribe(exception =>
            {
                GlobalVar.Manager?.Show(new Notification("Error",  exception.Message, NotificationType.Error));
            }).DisposeWith(disposable);
            
            SysPrintCommand.ThrownExceptions.Subscribe(exception =>
            {
                GlobalVar.Manager?.Show(new Notification("Error",  exception.Message, NotificationType.Error));
            }).DisposeWith(disposable);

            if (Design.IsDesignMode)return;

            Observable.Interval(TimeSpan.FromSeconds(10))
                .Select(_ => Unit.Default)
                .InvokeCommand(RawRefreshCommand)
                .DisposeWith(disposable);

            if (!_inited)
            {
                _inited = true;
                Observable.Return(Unit.Default)
                    .InvokeCommand(RefreshAllCommand)
                    .DisposeWith(disposable);
            }
        });
    }

    private async Task _doTextRefresh()
    {
        SystemInfo = "Loading";
        
        var result = await GlobalCfg.SysCompleteInfo
            .WithTimeout(TimeSpan.FromSeconds(GlobalCfg.DefaultRequestTimeout))
            .PostAsync()
            .ReceiveString();

        var deserializeObject = JsonConvert.DeserializeObject<JObject>(result);

        var res = deserializeObject?["data"]?.ToString();

        SystemInfo = string.IsNullOrWhiteSpace(res) ? "NO DATA" : res;
    }

    private async Task _doRawRefresh()
    {
        // get cpu
        CpuUtilization = $"{await _doFetchRaw("cpu_utilization")}%";
        CpuTemp =  $"{await _doFetchRaw("cpu_temp")}°C";
        var rawRam = JsonConvert.DeserializeObject<JObject>(await _doFetchRaw("current_ram"));
        MemUtilization = $"{rawRam["used"]}/{rawRam["total"]}";
        
        var rawLoad = JsonConvert.DeserializeObject<JObject>(await _doFetchRaw("load_avg"));
        SysLoad = $"{rawLoad["1_min_avg"]} / {rawLoad["5_min_avg"]} / {rawLoad["15_min_avg"]}";
    }

    private async Task<string> _doFetchRaw(string req)
    {
        var result = await GlobalCfg.RawInfo
            .WithTimeout(TimeSpan.FromSeconds(GlobalCfg.DefaultRequestTimeout))
            .PostJsonAsync(new
            {
                req
            })
            .ReceiveString();
        // Console.WriteLine(result);
        var deserializeObject = JsonConvert.DeserializeObject<JObject>(result);
        return deserializeObject?["data"]?.ToString() ?? "?";
    }

    private async Task _doPrintSysInfo()
    {
        var result = await GlobalCfg.ThermalOnline
            .WithTimeout(TimeSpan.FromSeconds(GlobalCfg.DefaultRequestTimeout))
            .PostJsonAsync(new { })
            .ReceiveString();
        if (JsonConvert.DeserializeObject<JObject>(result)["code"].ToString() != "200") throw new Exception("Printer offline!");
        
        result = await GlobalCfg.ThermalSysPrint
            .WithTimeout(TimeSpan.FromSeconds(GlobalCfg.DefaultRequestTimeout))
            .PostJsonAsync(new { })
            .ReceiveString();
        if (JsonConvert.DeserializeObject<JObject>(result)["code"].ToString() != "200") throw new Exception("Error occured!");
        GlobalVar.Manager?.Show(new Notification("Success", "Successfully requested", NotificationType.Success));
    }
}