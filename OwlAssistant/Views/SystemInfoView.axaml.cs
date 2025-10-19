using Avalonia;
using Avalonia.Controls;
using Avalonia.Markup.Xaml;
using Avalonia.ReactiveUI;
using OwlAssistant.ViewModels;

namespace OwlAssistant.Views;

public partial class SystemInfoView : ReactiveUserControl<SystemInfoViewModel>
{
    public SystemInfoView()
    {
        InitializeComponent();
    }
}