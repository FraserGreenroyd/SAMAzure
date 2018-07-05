using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace AzureEngine.Utilities
{
    public static class RadianceUtility
    {
        private static String shellFile = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData) + @"\Grasshopper\Libraries\Azure\radInstall.sh";
        public static String ShellFile { get { return shellFile; } set { shellFile = value; } }
    }
}