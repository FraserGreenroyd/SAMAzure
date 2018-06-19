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
            Program p = new Program();
            p.Run();
        }

        public async void Run()
        {
            AzureEngine ae = new AzureEngine();
            ae.InitStorage();
            Console.WriteLine("Press any key to upload the test file");
            Console.ReadLine();
            ae.SendFile(@"C:\Users\fgreenro\Documents\Repo Code\Test Files & Scripts\", "AzureTest2.txt").GetAwaiter().GetResult();
            Console.WriteLine("Press any key to delete the blob");
            Console.ReadLine();
            ae.DeleteBlob().GetAwaiter().GetResult();

            Console.WriteLine("Press any key to exit...");
            Console.ReadLine();
        }
    }
}
