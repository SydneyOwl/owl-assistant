using System;
using System.Threading.Tasks;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Controls.ApplicationLifetimes;
using Avalonia.Controls.Notifications;
using Avalonia.Markup.Xaml;
using Flurl.Http;
using OwlAssistant.Resources;
using OwlAssistant.ViewModels;
using OwlAssistant.Views;
using Serilog;
using Serilog.Events;

namespace OwlAssistant;

public partial class App : Application
{
    public override void Initialize()
    {
        AvaloniaXamlLoader.Load(this);
    }

    public override void OnFrameworkInitializationCompleted()
    {
        
        if (!OperatingSystem.IsBrowser())
        {
            FlurlHttp.ConfigureClientForUrl(GlobalCfg.GlobalAddr)
                .ConfigureInnerHandler((handler) =>
                    {
                        handler.ServerCertificateCustomValidationCallback = (message, cert, chain, errors) => true;
                    }
                );
        }
        
        Log.Logger = new LoggerConfiguration()
            .MinimumLevel.Debug()
            .MinimumLevel.Override("Microsoft", LogEventLevel.Information)
            .Enrich.FromLogContext()
            .WriteTo.Console()
            .WriteTo.Debug()
            .CreateLogger();

        AppDomain.CurrentDomain.UnhandledException += (s, e) => Log.Write(LogEventLevel.Error, (Exception)e.ExceptionObject, "Unhandled exception");
        TaskScheduler.UnobservedTaskException += (s, e) => Log.Write(LogEventLevel.Error, e.Exception, "Unobserved task exception");

        
        if (ApplicationLifetime is IClassicDesktopStyleApplicationLifetime desktop)
        {
            desktop.MainWindow = new MainWindow
            {
                DataContext = new MainWindowViewModel()
            };
            
            GlobalVar.Manager = new WindowNotificationManager(desktop.MainWindow);
            GlobalVar.TopLevel = desktop.MainWindow;
        }
        else if (ApplicationLifetime is ISingleViewApplicationLifetime singleViewPlatform)
        {
            singleViewPlatform.MainView = new MainView()
            {
                DataContext = new MainWindowViewModel()
            };
            GlobalVar.Manager = new WindowNotificationManager(TopLevel.GetTopLevel(singleViewPlatform.MainView));
            GlobalVar.TopLevel = TopLevel.GetTopLevel(singleViewPlatform.MainView);
        }

        base.OnFrameworkInitializationCompleted();
    }
}