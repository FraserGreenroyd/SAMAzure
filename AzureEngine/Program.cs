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

        SystemMessageContainer systemMessages;

        public async void Run()
        {
            systemMessages = new SystemMessageContainer();
            systemMessages.MessagesUpdated += SystemMessages_MessagesUpdated;

            AzureEngine ae = new AzureEngine(systemMessages);
            ae.CreateAzureConnection(@"C:\Users\fgreenro\Documents\Repo Code\SAM\AzureEngine\AzureEngine\azureauth.properties", "azureAutoTest", "West Europe");
            ae.CreateVirtualMachine();
            ae.CreateBlobStorage(@"DefaultEndpointsProtocol=https;AccountName=azureenginetest123;AccountKey=CHR1QTB2tqY21biqzn+UKSn3yNqmSWFAT2lZK9eJ1vGnP9Q6tvafRZgOlbTOu6lgqW+0OBxf5wPxPq8XWRAtTg==;EndpointSuffix=core.windows.net");

            ae.CreateBatchClient("enginebatchtest123", @"xTQl3xJIJ/D6mZDoEysL0R3q9ko1y0vX6awmQzrPmyZcP7xJT/OioXGvqMpRF6736OxYSE+B/aJ/moOf+WXIlQ==", "https://enginebatchtest123.westeurope.batch.azure.com", "azureBatchPoolTest", "azureBatchJobTest", 2, "Basic_A1");

            ae.SendFile(@"C:\Users\fgreenro\Documents\Repo Code\Test Files & Scripts\", "SimpleTask.py");

            Console.WriteLine("Wait for file to upload - press k to continue");
            if (Console.ReadLine().ToUpper() == "K")
            {
                ae.AddTask("python SimpleTask.py Hello World", "SimpleTask.py");
                ae.MoveCompletedTaskFiles();
            }

            /*ae.InitStorage();
            Console.WriteLine("Press any key to upload the test file");
            Console.ReadLine();
            ae.SendFile(@"C:\Users\fgreenro\Documents\Repo Code\Test Files & Scripts\", "AzureTest.txt").GetAwaiter().GetResult();
            Console.WriteLine("Press the D key to download the test file. Press any other key to skip");
            if(Console.ReadLine().ToUpper() == "D")
                ae.DownloadFile(@"C:\Users\fgreenro\Documents\Repo Code\Test Files & Scripts\", "AzureDownload.txt", "AzureTest.txt").GetAwaiter().GetResult();
            Console.WriteLine("Press any key to delete the blob");
            Console.ReadLine();
            ae.DeleteBlob().GetAwaiter().GetResult();*/

            //ae.SpinUpVM();
            Console.WriteLine("Press D to delete the VM and associated resources");
            if (Console.ReadLine().ToUpper() == "D")
            {
                ae.DeallocateVM();
                ae.DeleteResourceGroup();
            }
            else
            {
                Console.WriteLine("Powering down VM...");
                ae.SwitchOff();
            }

            Console.WriteLine("Press any key to exit...");
            Console.ReadLine();
        }

        private void SystemMessages_MessagesUpdated(object sender, System.ComponentModel.PropertyChangedEventArgs e)
        {
            SystemMessage sm = systemMessages.GetLatestMessage();
            Console.WriteLine(sm.TimeStamp + ": " + sm.GetType() + sm.Message);
            if (sm.Type == SystemMessage.MessageType.Error)
                Console.WriteLine(sm.ErrorDetails);

            Console.WriteLine();
        }
    }
}
