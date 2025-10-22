using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reactive;
using System.Reactive.Disposables;
using System.Reactive.Linq;
using System.Threading.Tasks;
using Avalonia.Controls;
using Avalonia.Controls.Notifications;
using Avalonia.Media;
using Avalonia.Threading;
using DynamicData;
using Flurl.Http;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using OwlAssistant.Resources;
using Plugin.AudioRecorder;
using ReactiveUI;
using ReactiveUI.Fody.Helpers;
using Serilog;
using Notification = Avalonia.Controls.Notifications.Notification;

namespace OwlAssistant.ViewModels;

public class ATISInfoViewModel : ViewModelBase
{
    [Reactive] public IImmutableSolidColorBrush ATISStatusColor { get; set; } = Brushes.OrangeRed;
    [Reactive] public IImmutableSolidColorBrush RecStatusColor { get; set; } = Brushes.CornflowerBlue;
    [Reactive] public double MasterVolume { get; set; } = 0;
    [Reactive] public double MusicVolume { get; set; } = 0;
    [Reactive] public bool MusicStop { get; set; }
    [Reactive] public double ATISVolume { get; set; } = 0;
    [Reactive] public bool ATISStop { get; set; }
    
    [Reactive] public bool CampusEnabled { get; set; }
    [Reactive] public double BacklightTimeout { get; set; } = 0;
    [Reactive] public double TxFrequency { get; set; } = 0;
    
    [Reactive] public string SelectedSong { get; set; } = string.Empty;
    
    [Reactive] public bool IsContentOpened { get; set; } = false;

    [Reactive]
    public ObservableCollection<string> SongList { get; set; } = [];
    

    public ReactiveCommand<Unit, Unit> CheckATISCommand { get; }
    public ReactiveCommand<Unit, Unit> RefreshCommand { get; }
    public ReactiveCommand<Unit, Unit> ApplyTxFreq { get; }
    public ReactiveCommand<Unit, Unit> ResetAll { get; }
    public ReactiveCommand<Unit, Unit> GoRepo { get; }
    
    public ReactiveCommand<Unit, Unit> ChangeRecordStatus { get; }


    private bool _recording;
    private AudioRecorderService _recorder;
    private string _tmpFilePath;

    public ATISInfoViewModel()
    {
        RefreshCommand = ReactiveCommand.CreateFromTask(()=>Task.CompletedTask);
        GoRepo = ReactiveCommand.CreateFromTask(async ()=>
        {
            await GlobalVar.TopLevel!.Launcher.LaunchUriAsync(
                new Uri("https://github.com/SydneyOwl/owl-assistant"));
            return;
        });
        if (OperatingSystem.IsBrowser())return;
        IsContentOpened = true;
        _recorder = new AudioRecorderService
        {
            StopRecordingOnSilence = false,
            StopRecordingAfterTimeout = false,
            SilenceThreshold = 0f
        };

        _recorder.AudioInputReceived += Recorder_AudioInputReceived;
        
        CheckATISCommand = ReactiveCommand.CreateFromTask(_checkATIS);
        RefreshCommand = ReactiveCommand.CreateFromTask(_refreshConfig);
        ApplyTxFreq = ReactiveCommand.CreateFromTask(_applyTxFreq);
        ResetAll = ReactiveCommand.CreateFromTask(_resetAll);
        ChangeRecordStatus = ReactiveCommand.CreateFromTask(async () =>
        {
            _recording = !_recording;
            if (_recording)
            {
                await _startRecord();
                return;
            }
            await _stopRecord();
        });
        
        this.WhenActivated(disposable =>
        {
            CheckATISCommand.ThrownExceptions.Subscribe(ex =>
            {
                ATISStatusColor = Brushes.OrangeRed;
                GlobalVar.Manager?.Show(new Notification("Error", ex.Message, NotificationType.Error));
            }); 
            RefreshCommand.ThrownExceptions.Subscribe(ex =>
            {
                GlobalVar.Manager?.Show(new Notification("Error", ex.Message, NotificationType.Error));
            });
            ApplyTxFreq.ThrownExceptions.Subscribe(ex =>
            {
                GlobalVar.Manager?.Show(new Notification("Error", ex.Message, NotificationType.Error));
            });
            ResetAll.ThrownExceptions.Subscribe(ex =>
            {
                GlobalVar.Manager?.Show(new Notification("Error", ex.Message, NotificationType.Error));
            });  
            ChangeRecordStatus.ThrownExceptions.Subscribe(async void (ex) =>
            {
                Log.Error(ex.StackTrace);
                GlobalVar.Manager?.Show(new Notification("Error", ex.Message, NotificationType.Error));
                _recording = false;
                 await _stopRecord();
            });
            
            if (Design.IsDesignMode)return;
            
            Observable.Return(Unit.Default)
                .Subscribe(async _ =>
                {
                    await _exWrapper(_refreshConfig());
        
                    this.WhenAnyValue(
                            x => x.MasterVolume,
                            x => x.ATISVolume,
                            x => x.MusicVolume,
                            x => x.ATISStop,
                            x => x.MusicStop)
                        .Skip(1)
                        .Throttle(TimeSpan.FromMilliseconds(300))
                        .SelectMany(async _ =>
                        {
                            Log.Debug("Volume config changed by user");
                            await _exWrapper(_sendVolConfig("music", MusicVolume.ToString(CultureInfo.InvariantCulture)));
                            await _exWrapper(_sendVolConfig("atis", ATISVolume.ToString(CultureInfo.InvariantCulture)));
                            await _exWrapper(_sendFMConfig("setVolume", MasterVolume.ToString(CultureInfo.InvariantCulture)), 
                                "True", "Error while setting mater volume!");
                            await _exWrapper(_sendStartStopConfig("music", MusicStop ? "off" : "on"));
                            await _exWrapper(_sendStartStopConfig("atis", ATISStop ? "off" : "on"));
                            return Unit.Default;
                        })
                        .Subscribe()
                        .DisposeWith(disposable);
                    
                    this.WhenAnyValue(
                            x => x.CampusEnabled,
                            x => x.BacklightTimeout)
                        .Skip(1)
                        .Throttle(TimeSpan.FromMilliseconds(300))
                        .SelectMany(async _ =>
                        {
                            Log.Debug("FM config changed by user");
                            await _exWrapper(_sendFMConfig("setCampus", CampusEnabled ? "1" : "0"), 
                                "True", "Error while setting campus status!");
                            await _exWrapper(_sendFMConfig("setBacklight", BacklightTimeout.ToString(CultureInfo.InvariantCulture)), 
                                "True", "Error while setting backlight!");
                            return Unit.Default;
                        })
                        .Subscribe()
                        .DisposeWith(disposable);
                    
                    this.WhenAnyValue(x => x.SelectedSong)
                        .Skip(1)
                        .Throttle(TimeSpan.FromMilliseconds(300))
                        .SelectMany(async _ =>
                        {
                            Log.Debug("Song config changed by user");
                            await _exWrapper(_sendChangeSongConfig(SelectedSong));
                            return Unit.Default;
                        })
                        .Subscribe()
                        .DisposeWith(disposable);
                })
                .DisposeWith(disposable);
            
            // update printer status
            Observable.Timer(TimeSpan.FromMilliseconds(300), TimeSpan.FromSeconds(5))
                .Select(_ => Unit.Default)
                .InvokeCommand(CheckATISCommand)
                .DisposeWith(disposable);
        });
    }
    
    private async Task _checkATIS()
    {
        if (!await _checkFMOnline())
        {
            ATISStatusColor = Brushes.OrangeRed;
            // Log.Debug("FM not online");
            return;
        };
        ATISStatusColor = Brushes.LimeGreen;
        // Log.Debug("FM online");
    }

    private async Task<bool> _checkFMOnline()
    {
        var sendFMConfig = await _sendFMConfig("isopen");
        return sendFMConfig == "True";
    }

    private async Task<string> _sendFMConfig(string tp, string? val = null)
    {
        var result = await GlobalCfg.ATISModifyFM
            .WithTimeout(TimeSpan.FromSeconds(GlobalCfg.DefaultRequestTimeout))
            .PostJsonAsync(new
            {
                instruction = tp,
                targetM = val
            })
            .ReceiveString();
        var res = JsonConvert.DeserializeObject<JObject>(result)!;
        if (res["code"]!.ToString() == "0") throw new Exception("Device offline!");
        if (res["code"]!.ToString() != "200") throw new Exception("Error while sending instructions!");

        return res["result"]!.ToString();
    }
    
    private async Task _sendVolConfig(string target, string status)
    {
        var result = await GlobalCfg.ATISModifyVolume
            .WithTimeout(TimeSpan.FromSeconds(GlobalCfg.DefaultRequestTimeout))
            .PostJsonAsync(new
            {
                status,
                target
            })
            .ReceiveString();
        
        var res = JsonConvert.DeserializeObject<JObject>(result)!;
        if (res["code"]!.ToString() == "0") throw new Exception("Device offline!");
        if (res["code"]!.ToString() != "200") throw new Exception("Error while change volume!");
    }
    
    private async Task _sendStartStopConfig(string target, string status)
    {
        var result = await GlobalCfg.ATISStartStop
            .WithTimeout(TimeSpan.FromSeconds(GlobalCfg.DefaultRequestTimeout))
            .PostJsonAsync(new
            {
                status,
                target
            })
            .ReceiveString();
        
        var res = JsonConvert.DeserializeObject<JObject>(result)!;
        if (res["code"]!.ToString() != "200") throw new Exception("Error while change volume!");
    }
    
    private async Task _sendChangeSongConfig(string song)
    {
        var result = await GlobalCfg.ATISChgSong
            .WithTimeout(TimeSpan.FromSeconds(GlobalCfg.DefaultRequestTimeout))
            .PostJsonAsync(new
            {
               song
            })
            .ReceiveString();
        
        var res = JsonConvert.DeserializeObject<JObject>(result)!;
        if (res["code"]!.ToString() != "200") throw new Exception("Error while change song!");
    }

    private async Task _exWrapper(Task<string> task, string? expectedVal, string? errMsg, bool doThrow = false)
    {
        try
        {
            var res = await task;
            if (expectedVal is null)return;
            if (res is null) throw new Exception("Result cannot be null!");
            if (!res.Equals(expectedVal))  throw new Exception(errMsg ?? "Error occurred!");
        }
        catch (Exception e)
        {
            if (doThrow) throw;
            Log.Error(e.Message);
            Dispatcher.UIThread.Invoke(() =>
            {
                GlobalVar.Manager?.Show(new Notification("Error", e.Message, NotificationType.Error));
            });
        }
    }
    
    private async Task _exWrapper(Task task)
    {
        try
        {
            await task;
        }
        catch (Exception e)
        {
            Console.WriteLine(e.StackTrace);
            Log.Error(e.Message);
            Dispatcher.UIThread.Invoke(() =>
            {
                GlobalVar.Manager?.Show(new Notification("Error", e.Message, NotificationType.Error));
            });
        }
    }

    private async Task _applyTxFreq()
    {
        if (TxFrequency < 760)throw new Exception("Invalid input!");
        if (TxFrequency < 870 && !CampusEnabled)throw new Exception("Enable campus first!");
        if (TxFrequency > 1080) throw new Exception("Invalid input!");
        if (await _sendFMConfig("setFrequency", TxFrequency.ToString(CultureInfo.InvariantCulture)) != "True")
        {
            throw new Exception("Error while setting frequency!");
        }
    }
    
    private async Task _resetAll()
    {
        if (await _sendFMConfig("reset") != "True")
        {
            throw new Exception("Error while resetting!");
        }
    }

    private async Task _refreshConfig()
    {
        var result = await GlobalCfg.ATISVolInfo
            .WithTimeout(TimeSpan.FromSeconds(GlobalCfg.DefaultRequestTimeout))
            .PostJsonAsync(new{})
            .ReceiveString();
        
        var res = JsonConvert.DeserializeObject<JObject>(result)!;
        
        ATISVolume = res["atis"]!.ToObject<double>();
        MusicVolume = res["music"]!.ToObject<double>();
        ATISStop = res["stopATIS"]!.ToObject<bool>();
        MusicStop = res["stopMusic"]!.ToObject<bool>(); 
        
        SongList.Clear();
        var tmpList = res["totalSong"]!.ToObject<List<string>>()!;
        SongList.AddRange(tmpList);
        SelectedSong = res["currentSong"].ToString();

        result = await _sendFMConfig("getCurrent");
        res = JsonConvert.DeserializeObject<JObject>(result)!;

        MasterVolume = res["vol"].ToObject<double>();
        TxFrequency = res["fre"].ToObject<double>();
        BacklightTimeout = res["bak"].ToObject<double>();
        CampusEnabled = res["camp"].ToObject<bool>();
    }

    private async Task _startRecord()
    {
        Log.Information("Start record...");
        _recording = true;
        RecStatusColor = Brushes.Orange;
        await _recorder.StartRecording();
    }

    private async Task _stopRecord()
    {
        try
        {
            _recording = false;
            RecStatusColor = Brushes.CornflowerBlue;
            await _recorder?.StopRecording()!;
        }
        catch (Exception e)
        {
            // ignored
            GlobalVar.Manager?.Show(new Notification("Warning", e.Message, NotificationType.Warning));
        }
    }
    
    private async void Recorder_AudioInputReceived(object? sender, string audioFile)
    {
        try
        {
            Log.Information($"Audio Input Received: {audioFile}");
        
            await GlobalCfg.ATISUploadRecording
                .PostMultipartAsync(multipart => 
                    multipart.AddFile("file",audioFile,fileName:"file")
                )
                .ReceiveString();
            Log.Information($"Audio Input Uploaded.");
        }
        catch (Exception e)
        {
            Log.Error(e.Message);
            GlobalVar.Manager?.Show(new Notification("Warning", e.Message, NotificationType.Warning));
        }
    }
    
}