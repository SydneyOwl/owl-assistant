using System;
using System.Reactive;
using Avalonia.Media;
using OwlAssistant.Resources;
using ReactiveUI;
using ReactiveUI.Fody.Helpers;

namespace OwlAssistant.ViewModels;

public class MainWindowViewModel : ViewModelBase
{
    public string Greeting { get; } = "Welcome to Avalonia!";

    public MainWindowViewModel()
    { 
        SystemInfoViewModel = new SystemInfoViewModel();
        SensorInfoViewModel = new SensorInfoViewModel();
        PrintInfoViewModel = new PrintInfoViewModel();
        AtisInfoViewModel = new ATISInfoViewModel();

        IsFRP = GlobalCfg.UseFrp;
    }

    [Reactive] public bool IsFRP { get; set; } = false;
    
    [Reactive] public SystemInfoViewModel? SystemInfoViewModel { get; set; }
    [Reactive] public SensorInfoViewModel? SensorInfoViewModel { get; set; }
    [Reactive] public PrintInfoViewModel? PrintInfoViewModel { get; set; }
    [Reactive] public ATISInfoViewModel? AtisInfoViewModel { get; set; }
}