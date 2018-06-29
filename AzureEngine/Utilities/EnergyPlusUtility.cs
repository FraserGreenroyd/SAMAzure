using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace AzureEngine.Utilities
{
    public static class EnergyPlusUtility
    {
        private static List<String> epInstallCommands = new List<string>();
        
        public static void BuildEPInstallCommands()
        {
            epInstallCommands.Add("apt-get update");
            epInstallCommands.Add("rm -rf /var/lib/apt/lists/*");
            epInstallCommands.Add("curl -SLO https://github.com/NREL/EnergyPlus/releases/download/v8.8.0/EnergyPlus-8.8.0-7c3bbe4830-Linux-x86_64.sh #");
            epInstallCommands.Add("chmod +x EnergyPlus-8.8.0-7c3bbe4830-Linux-x86_64.sh #");
            epInstallCommands.Add("echo \"y\r\" | ./EnergyPlus-8.8.0-7c3bbe4830-Linux-x86_64.sh #");
            epInstallCommands.Add("rm EnergyPlus-8.8.0-7c3bbe4830-Linux-x86_64.sh #");
            epInstallCommands.Add("cd /usr/local/EnergyPlus-8-8-0 #");
            epInstallCommands.Add("rm -rf DataSets Documentation ExampleFiles WeatherData MacroDataSets PostProcess/convertESOMTRpgm PostProcess/EP-Compare PreProcess/FMUParser PreProcess/ParametricPreProcessor PreProcess/IDFVersionUpdater #");
            epInstallCommands.Add("cd /usr/local/bin #");
            epInstallCommands.Add("find -L . -type l -delete #");
        }

        public static String CompileEPInstallCommand()
        {
            if (epInstallCommands.Count == 0)
                BuildEPInstallCommands();
            String s = "";
            for(int x = 0; x < epInstallCommands.Count; x++)
                s += epInstallCommands[x] + " && ";

            s = s.Substring(0, s.LastIndexOf(" && "));

            return s;
        }
    }
}
