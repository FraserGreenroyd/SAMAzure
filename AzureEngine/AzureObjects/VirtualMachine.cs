using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

using Microsoft.Azure.Management.Compute.Fluent;
using Microsoft.Azure.Management.Compute.Fluent.Models;
using Microsoft.Azure.Management.Network.Fluent;

using AzureEngine.Utilities;

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
            String region = AzureConnectionUtility.Region;
            String resourceGroup = AzureConnectionUtility.ResourceGroup;

            IAvailabilitySet availabilitySet = CreateAvailabilitySetIfNotExists();
            IPublicIPAddress publicIPAddress = CreateIPIfNotExists();
            INetwork network = CreateNetworkIfNotExists();
            INetworkInterface networkInterface = CreateNetworkInterfaceIfNotExists(network, publicIPAddress);
            
            messageContainer.AddInformationMessage("Configuring virtual machine...");
            String machineName = "azureAutoEngine_VM";
            virtualMachine = azureConnection.AzureLink.VirtualMachines.GetByResourceGroup(AzureConnectionUtility.ResourceGroup, machineName);

            if(virtualMachine == null)
            {
                messageContainer.AddInformationMessage("Creating virtual machine...");
                virtualMachine = azureConnection.AzureLink.VirtualMachines.Define(machineName)
                                            .WithRegion(AzureConnectionUtility.Region)
                                            .WithExistingResourceGroup(AzureConnectionUtility.ResourceGroup)
                                            .WithExistingPrimaryNetworkInterface(networkInterface)
                                            .WithLatestLinuxImage("credativ", "Debian", "8")
                                            .WithRootUsername("azureUser")
                                            .WithRootPassword("Azure12345678")
                                            .WithComputerName("azureAutoEngineVM")
                                            .WithExistingAvailabilitySet(availabilitySet)
                                            .WithSize(VirtualMachineSizeTypes.BasicA1)
                                            .Create();
                messageContainer.AddInformationMessage("Virtual machine created...");
            }

            if(virtualMachine.PowerState != PowerState.Running)
                SwitchOnVM();

            messageContainer.AddInformationMessage("Virtual machine configured... feel free to inspect it on the portal...");
        }

        private IAvailabilitySet CreateAvailabilitySetIfNotExists()
        {
            messageContainer.AddInformationMessage("Configuring availability set...");

            String setName = "azureAutoEngine_AvailabilitySet";
            IAvailabilitySet availabilitySet = azureConnection.AzureLink.AvailabilitySets.GetByResourceGroup(AzureConnectionUtility.ResourceGroup, setName);

            if (availabilitySet == null)
            {
                messageContainer.AddInformationMessage("Creating availability set...");

                availabilitySet = azureConnection.AzureLink.AvailabilitySets.Define(setName)
                                            .WithRegion(AzureConnectionUtility.Region)
                                            .WithExistingResourceGroup(AzureConnectionUtility.ResourceGroup)
                                            .WithSku(AvailabilitySetSkuTypes.Managed)
                                            .Create();

                messageContainer.AddInformationMessage("Availability set created...");
            }

            messageContainer.AddInformationMessage("Availability set configured...");

            return availabilitySet;
        }

        private IPublicIPAddress CreateIPIfNotExists()
        {
            messageContainer.AddInformationMessage("Configuring IP...");

            String ipName = "azureAutoEngine_IPAddress";
            IPublicIPAddress publicIPAddress = azureConnection.AzureLink.PublicIPAddresses.GetByResourceGroup(AzureConnectionUtility.ResourceGroup, ipName);

            if(publicIPAddress == null)
            {
                messageContainer.AddInformationMessage("Creating public IP...");
                publicIPAddress = azureConnection.AzureLink.PublicIPAddresses.Define(ipName)
                                            .WithRegion(AzureConnectionUtility.Region)
                                            .WithExistingResourceGroup(AzureConnectionUtility.ResourceGroup)
                                            .WithDynamicIP()
                                            .Create();

                messageContainer.AddInformationMessage("Public IP created...");
            }

            messageContainer.AddInformationMessage("IP configured...");

            return publicIPAddress;
        }

        private INetwork CreateNetworkIfNotExists()
        {
            messageContainer.AddInformationMessage("Configuring virtual network...");

            String networkName = "azureAutoEngine_Network";
            INetwork network = azureConnection.AzureLink.Networks.GetByResourceGroup(AzureConnectionUtility.ResourceGroup, networkName);

            if(network == null)
            {
                messageContainer.AddInformationMessage("Creating virtual network...");
                network = azureConnection.AzureLink.Networks.Define(networkName)
                                            .WithRegion(AzureConnectionUtility.Region)
                                            .WithExistingResourceGroup(AzureConnectionUtility.ResourceGroup)
                                            .WithAddressSpace("10.0.0.0/16")
                                            .WithSubnet("azureAutoEngine_Subnet", "10.0.0.0/24")
                                            .Create();

                messageContainer.AddInformationMessage("Virtual network created...");
            }

            messageContainer.AddInformationMessage("Virtual network configured...");

            return network;
        }

        private INetworkInterface CreateNetworkInterfaceIfNotExists(INetwork network, IPublicIPAddress publicIPAddress)
        {
            messageContainer.AddInformationMessage("Configuring network interface...");

            String interfaceName = "azureAutoEngine_NetworkInterface";
            INetworkInterface networkInterface = azureConnection.AzureLink.NetworkInterfaces.GetByResourceGroup(AzureConnectionUtility.ResourceGroup, interfaceName);

            if(networkInterface == null)
            {
                messageContainer.AddInformationMessage("Creating network interface...");
                networkInterface = azureConnection.AzureLink.NetworkInterfaces.Define("azureAutoEngine_NetworkInterface")
                                            .WithRegion(AzureConnectionUtility.Region)
                                            .WithExistingResourceGroup(AzureConnectionUtility.ResourceGroup)
                                            .WithExistingPrimaryNetwork(network)
                                            .WithSubnet("azureAutoEngine_Subnet")
                                            .WithPrimaryPrivateIPAddressDynamic()
                                            .WithExistingPrimaryPublicIPAddress(publicIPAddress)
                                            .Create();
                messageContainer.AddInformationMessage("Network interface created...");
            }
            
            messageContainer.AddInformationMessage("Network interface configured...");

            return networkInterface;
        }

        public List<String> Details()
        {
            List<String> rtn = new List<string>();

            if (virtualMachine == null)
                rtn.Add("Virtual Machine has not been initialised");
            else
            {
                rtn.Add("VM Size = " + virtualMachine.Size);
                rtn.Add("Storage size = " + virtualMachine.StorageProfile.OsDisk.DiskSizeGB + "gb");

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

        public void SwitchOnVM()
        {
            if (virtualMachine == null) return;

            virtualMachine.Start();
        }

        public void SwitchOffVM()
        {
            if (virtualMachine == null) return;

            virtualMachine.PowerOff();
            DeallocateVM();
        }

        public void DeallocateVM()
        {
            if (virtualMachine == null) return;
            virtualMachine.Deallocate();
        }
    }
}
