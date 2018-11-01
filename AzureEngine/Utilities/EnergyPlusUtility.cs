using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace AzureEngine.Utilities
{
    public static class EnergyPlusUtility
    {
        private static String shellFile = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData) + @"\Grasshopper\Libraries\Azure\epInstall.sh";
        public static String ShellFile { get { return shellFile; } set { shellFile = value; } }
    }
}
