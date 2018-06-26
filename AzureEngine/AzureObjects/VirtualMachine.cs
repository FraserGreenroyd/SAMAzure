using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

using Microsoft.Azure.Management.Compute.Fluent;
using Microsoft.Azure.Management.Compute.Fluent.Models;
using Microsoft.Azure.Management.Network.Fluent;

namespace AzureEngine.AzureObjects
{
    public class VirtualMachine
    {
        private IVirtualMachine virtualMachine = null;
        private VirtualMachineSizeTypes vmSize = null;
        private AzureConnection azureConnection = null;
        private SystemMessageContainer messageContainer = null;

        public VirtualMachine(AzureConnection connection, SystemMessageContainer container = null, VirtualMachineSizeTypes vmSize = null)
        {
            azureConnection = connection;
            if (vmSize == null)
                vmSize = VirtualMachineSizeTypes.BasicA1;

            this.vmSize = vmSize;

            messageContainer = (container == null ? new SystemMessageContainer() : container);
        }

        public void CreateVM()
        {
            String region = azureConnection.Region;
            String resourceGroup = azureConnection.ResourceGroup;

            messageContainer.AddInformationMessage("Configuring availability set...");
            IAvailabilitySet availabilitySet = azureConnection.AzureLink.AvailabilitySets.Define("azureAutoEngine_AvailabilitySet")
                                            .WithRegion(region)
                                            .WithExistingResourceGroup(resourceGroup)
                                            .WithSku(AvailabilitySetSkuTypes.Managed)
                                            .Create();
            messageContainer.AddInformationMessage("Availability set configured...");

            messageContainer.AddInformationMessage("Configuring IP...");
            IPublicIPAddress publicIPAddress = azureConnection.AzureLink.PublicIPAddresses.Define("azureAutoEngine_IPAddress")
                                            .WithRegion(region)
                                            .WithExistingResourceGroup(resourceGroup)
                                            .WithDynamicIP()
                                            .Create();
            messageContainer.AddInformationMessage("IP configured...");

            messageContainer.AddInformationMessage("Configuring virtual network...");
            INetwork network = azureConnection.AzureLink.Networks.Define("azureAutoEngine_network")
                                            .WithRegion(region)
                                            .WithExistingResourceGroup(resourceGroup)
                                            .WithAddressSpace("10.0.0.0/16")
                                            .WithSubnet("azureAutoEngine_Subnet", "10.0.0.0/24")
                                            .Create();
            messageContainer.AddInformationMessage("Virtual network configured...");

            messageContainer.AddInformationMessage("Configuring network interface...");
            INetworkInterface networkInterface = azureConnection.AzureLink.NetworkInterfaces.Define("azureAutoEngine_NetworkInterface")
                                            .WithRegion(region)
                                            .WithExistingResourceGroup(resourceGroup)
                                            .WithExistingPrimaryNetwork(network)
                                            .WithSubnet("azureAutoEngine_Subnet")
                                            .WithPrimaryPrivateIPAddressDynamic()
                                            .WithExistingPrimaryPublicIPAddress(publicIPAddress)
                                            .Create();
            messageContainer.AddInformationMessage("Network interface configured...");

            messageContainer.AddInformationMessage("Configuring virtual machine...");
            virtualMachine = azureConnection.AzureLink.VirtualMachines.Define("azureAutoEngine_VM")
                                            .WithRegion(region)
                                            .WithExistingResourceGroup(resourceGroup)
                                            .WithExistingPrimaryNetworkInterface(networkInterface)
                                            .WithLatestLinuxImage("credativ", "Debian", "8")
                                            .WithRootUsername("azureUser")
                                            .WithRootPassword("Azure12345678")
                                            .WithComputerName("azureAutoEngineVM")
                                            .WithExistingAvailabilitySet(availabilitySet)
                                            .WithSize(VirtualMachineSizeTypes.BasicA1)
                                            .Create();
            messageContainer.AddInformationMessage("Virtual machine configured... feel free to inspect it on the portal...");
        }

        public List<String> Details()
        {
            List<String> rtn = new List<string>();

            if (virtualMachine == null)
                rtn.Add("Virtual Machine has not been initialised");
            else
            {
                rtn.Add("VM Size = " + virtualMachine.Size);

                rtn.Add("Image Publisher = " + virtualMachine.StorageProfile.ImageReference.Publisher);
                rtn.Add("Image Offer = " + virtualMachine.StorageProfile.ImageReference.Offer);
                rtn.Add("Image SKU = " + virtualMachine.StorageProfile.ImageReference.Sku);
                rtn.Add("Image Version = " + virtualMachine.StorageProfile.ImageReference.Version);

                rtn.Add("OSDisk Type = " + virtualMachine.StorageProfile.OsDisk.OsType);
                rtn.Add("OSDisk Name = " + virtualMachine.StorageProfile.OsDisk.Name);

                rtn.Add("VM Computer Name = " + virtualMachine.OSProfile.ComputerName);
            }

            return rtn;
        }

        public void DeallocateVM()
        {
            virtualMachine.Deallocate();
        }
    }
}
