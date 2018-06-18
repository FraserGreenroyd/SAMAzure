using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace AzureEngine
{
    public class Program
    {
        public static void Main(String [] args)
        {
            AzureEngine ae = new AzureEngine();
            ae.InitStorage("test");

            System.Threading.Thread.Sleep(100000);
        }
    }
}
