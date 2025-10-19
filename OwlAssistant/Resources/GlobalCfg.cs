namespace OwlAssistant.Resources;

public class GlobalCfg
{
    public static string GlobalAddr = "https://scan.mrowl.xyz:5583/";
    
    public static string GlobalSensorAddr = "http://scan.mrowl.xyz:3649/";
    
    // public static string GlobalATISAddr = "http://scan.mrowl.xyz:9352/";

    public static string SysCompleteInfo = $"{GlobalAddr}thermal/fetchInfo";
    
    public static string RawInfo = $"{GlobalAddr}thermal/rawInfo";
    
    public static string ThermalOnline = $"{GlobalAddr}thermal/online";
    
    public static string ThermalSysPrint = $"{GlobalAddr}thermal/sysPrint";
    
    public static string ThermalPrint = $"{GlobalAddr}thermal/upload";
    
    public static string SensorData = $"{GlobalSensorAddr}getSensor";
    
    public static string SensorDataRange = $"{GlobalSensorAddr}getSensorDataByDateRange";
    
    public static string ATISModifyFM = $"{GlobalAddr}fm/modifyFM";
    
    public static string ATISModifyVolume = $"{GlobalAddr}fm/volume";
    
    public static string ATISStartStop = $"{GlobalAddr}fm/control";
    
    public static string ATISVolInfo = $"{GlobalAddr}fm/curVol";
    
    public static string ATISChgSong = $"{GlobalAddr}fm/chgSong";
    
    public static int RawInfoInterval = 5;

    public static int DefaultRequestTimeout = 10;

    public static string InsideSensorMac = "A4:C1:38:CF:B0:D6";
    
    public static string OutsideSensorMac = "A4:C1:38:D5:05:79";
}