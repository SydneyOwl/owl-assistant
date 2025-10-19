using System;
using System.Collections.ObjectModel;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Reactive;
using System.Reactive.Disposables;
using System.Reactive.Linq;
using System.Threading.Tasks;
using Avalonia.Controls;
using Avalonia.Controls.Notifications;
using Avalonia.Media;
using Avalonia.Platform.Storage;
using Flurl.Http;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using OwlAssistant.Resources;
using ReactiveUI;
using ReactiveUI.Fody.Helpers;
using Serilog;
using Notification = Avalonia.Controls.Notifications.Notification;

namespace OwlAssistant.ViewModels;

public class PrintInfoViewModel : ViewModelBase
{
    public ReactiveCommand<Unit, Unit> CheckPrinterCommand { get; }
    public ReactiveCommand<Unit, Unit> SelectImageAndPrintCommand { get; }
    public ReactiveCommand<Unit, Unit> TextPrintCommand { get; }
    public PrintInfoViewModel()
    {
        CheckPrinterCommand = ReactiveCommand.CreateFromTask(_checkPrinter);
        SelectImageAndPrintCommand = ReactiveCommand.CreateFromTask(_selectImage);
        TextPrintCommand = ReactiveCommand.CreateFromTask(_printText);
        
        this.WhenActivated(disposable =>
        {
            this.WhenAnyValue(x => x.TargetText)
                .Subscribe(x =>
                {
                    TextLength = $"Characters: {(x ?? string.Empty).Length}";
                })
                .DisposeWith(disposable);
            
            CheckPrinterCommand.ThrownExceptions.Subscribe(ex =>
            {
                PrinterStatusColor = Brushes.OrangeRed;
                GlobalVar.Manager?.Show(new Notification("Error", ex.Message, NotificationType.Error));
            });
            SelectImageAndPrintCommand.ThrownExceptions.Subscribe(ex =>
                GlobalVar.Manager?.Show(new Notification("Error", ex.Message, NotificationType.Error)));
            TextPrintCommand.ThrownExceptions.Subscribe(ex =>
                GlobalVar.Manager?.Show(new Notification("Error", ex.Message, NotificationType.Error)));
            
            
            if (Design.IsDesignMode)return;
            // update printer status
            Observable.Timer(TimeSpan.FromMilliseconds(300), TimeSpan.FromSeconds(5))
                .Select(_ => Unit.Default)
                .InvokeCommand(CheckPrinterCommand)
                .DisposeWith(disposable);
        });
    }

    private async Task<bool> _isPrinterOnline()
    {
        var result = await GlobalCfg.ThermalOnline
            .WithTimeout(TimeSpan.FromSeconds(GlobalCfg.DefaultRequestTimeout))
            .PostJsonAsync(new { })
            .ReceiveString();
        return JsonConvert.DeserializeObject<JObject>(result)["code"].ToString() == "200";
    }

    private async Task _checkPrinter()
    {
        if (!await _isPrinterOnline())
        {
            PrinterStatusColor = Brushes.OrangeRed;
            Log.Debug("Printer not online");
            return;
        };
        PrinterStatusColor = Brushes.LimeGreen;
        Log.Debug("Printer online");
    }

    private async Task _selectImage()
    {
        if (!await _isPrinterOnline())
        {
            throw new Exception("Printer offline!");
        }

        var openFilePickerAsync = await GlobalVar.TopLevel!.StorageProvider.OpenFilePickerAsync(new FilePickerOpenOptions
        {
            Title = "Select an image",
            AllowMultiple = false,
            FileTypeFilter = [FilePickerFileTypes.ImageAll]
        });
        if (openFilePickerAsync.Count == 0)return;

        await using var stream = await openFilePickerAsync.First().OpenReadAsync();
        if (stream.Length > 15 * 1024 * 1024) throw new Exception("Image is too large!");
        
        GlobalVar.Manager?.Show(new Notification("Notice", "Processing", NotificationType.Information));
        
        var receiveString = await GlobalCfg.ThermalPrint
            .PostMultipartAsync(multipart => 
                multipart.AddFile("file", stream,"file")
            )
            .ReceiveString();
        
        var tmp = JsonConvert.DeserializeObject<JObject>(receiveString);
        if (tmp is null) throw new Exception("Invalid data!");

        if (tmp["code"].ToString() == "200")
        {
            GlobalVar.Manager?.Show(new Notification("Success", "Successfully printed.", NotificationType.Success));
            return;
        }

        throw new Exception($"An error occurred.{tmp["msg"]?.ToString()}");
    }

    private async Task _printText()
    {
        if (!await _isPrinterOnline())
        {
            throw new Exception("Printer offline!");
        }

        if (TargetText.Length > 1000)
        {
            throw new Exception("Target text is too large!");
        }
        
        var receiveString = await GlobalCfg.ThermalPrint
            .PostUrlEncodedAsync(new
            {
                file = TargetText
            })
            .ReceiveString();
        
        var tmp = JsonConvert.DeserializeObject<JObject>(receiveString);
        if (tmp is null) throw new Exception("Invalid data!");

        if (tmp["code"].ToString() == "200")
        {
            GlobalVar.Manager?.Show(new Notification("Success", "Successfully printed.", NotificationType.Success));
            return;
        }

        throw new Exception($"An error occurred.{tmp["msg"]?.ToString()}");
        
    }
    
    [Reactive] public IImmutableSolidColorBrush PrinterStatusColor { get; set; } = Brushes.OrangeRed;
    [Reactive] public string TargetText { get; set; } = string.Empty;
    [Reactive] public string TextLength { get; set; }  =  "Characters: 0";
}