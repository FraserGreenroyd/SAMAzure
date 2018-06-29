using System;
using System.Collections.Generic;

using Grasshopper.Kernel;
using Rhino.Geometry;

using System.IO;

using AzureEngine;
using System.Threading.Tasks;

// In order to load the result of this wizard, you will also need to
// add the output bin/ folder of this project to the list of loaded
// folder in Grasshopper.
// You can use the _GrasshopperDeveloperSettings Rhino command for that.

namespace AzureGrasshopper
{
    public class AzureGrasshopperComponent : GH_Component
    {
        /// <summary>
        /// Each implementation of GH_Component must provide a public 
        /// constructor without any arguments.
        /// Category represents the Tab in which the component will appear, 
        /// Subcategory the panel. If you use non-existing tab or panel names, 
        /// new tabs/panels will automatically be created.
        /// </summary>
        public AzureGrasshopperComponent()
          : base("AzureGrasshopper", "SAPAzure_EP",
              "Run EnergyPlus simulations on Azure",
              "SAP", "Azure")
        {
        }

        /// <summary>
        /// Registers all the input parameters for this component.
        /// </summary>
        protected override void RegisterInputParams(GH_Component.GH_InputParamManager pManager)
        {
            pManager.AddTextParameter("Project Number", "Project Number", "The project number for the project being simulated", GH_ParamAccess.item);
            pManager.AddTextParameter("Project Name", "Project Name", "The project name for the project being simulated", GH_ParamAccess.item);
            pManager.AddTextParameter("EPW File", "EPW File", "The location on your system (full file path) to the EPW file to include for simulation", GH_ParamAccess.item);
            pManager.AddTextParameter("IDF Files", "IDF Files", "The location on your system (full file path) to the IDF file(s) to simulate", GH_ParamAccess.list);
            pManager.AddBooleanParameter("Run", "Run", "Do you wish to run this component?", GH_ParamAccess.item);
        }

        /// <summary>
        /// Registers all the output parameters for this component.
        /// </summary>
        protected override void RegisterOutputParams(GH_Component.GH_OutputParamManager pManager)
        {
            pManager.AddBooleanParameter("Complete", "Complete", "Has everything completed successfully?", GH_ParamAccess.item);
        }

        /// <summary>
        /// This is the method that actually does the work.
        /// </summary>
        /// <param name="DA">The DA object can be used to retrieve data from input parameters and 
        /// to store data in output parameters.</param>
        protected override async void SolveInstance(IGH_DataAccess DA)
        {
            String pNumber = null;
            DA.GetData(0, ref pNumber);
            if (pNumber == null)
                AddRuntimeMessage(GH_RuntimeMessageLevel.Error, "Please provide a valid project number");

            String pName = null;
            DA.GetData(1, ref pName);
            if (pName == null)
                AddRuntimeMessage(GH_RuntimeMessageLevel.Error, "Please provide a valid project name");

            String epwFile = null;
            DA.GetData(2, ref epwFile);
            if (epwFile == null)
                AddRuntimeMessage(GH_RuntimeMessageLevel.Error, "Please provide a valid EPW file");

            if (!File.Exists(epwFile))
                AddRuntimeMessage(GH_RuntimeMessageLevel.Error, "Please provide a valid, existing, EPW file");

            List<String> idfFiles = new List<string>();
            DA.GetDataList(3, idfFiles);
            if (idfFiles.Count == 0)
                AddRuntimeMessage(GH_RuntimeMessageLevel.Error, "Please provide a valid list of IDF files");

            if (!AllValidFiles(idfFiles))
                AddRuntimeMessage(GH_RuntimeMessageLevel.Error, "Please provide a list of valid, existing, IDF files");

            bool run = false;
            DA.GetData(4, ref run);

            if (pNumber == null || pName == null || epwFile == null || idfFiles.Count == 0 || !File.Exists(epwFile) || !AllValidFiles(idfFiles) || !run)
                return;

            //Everything is valid - let's run a simulation!
            AZEngine aEngine = new AZEngine(pNumber, pName);
            aEngine.CreateBlobStorage();

            aEngine.CreateBatchClients(idfFiles.Count);

            aEngine.InstallEnergyPlus();

            aEngine.UploadFile(epwFile);
            aEngine.UploadFiles(idfFiles);

            aEngine.RunEnergyPlus(idfFiles, epwFile);

            if (aEngine.TrueWhenTasksComplete())
                DA.SetData(0, true);
        }

        private bool AllValidFiles(List<String> list)
        {
            bool allValid = true;
            foreach (String s in list)
                allValid &= File.Exists(s);

            return allValid;
        }

        /// <summary>
        /// Provides an Icon for every component that will be visible in the User Interface.
        /// Icons need to be 24x24 pixels.
        /// </summary>
        protected override System.Drawing.Bitmap Icon
        {
            get
            {
                // You can add image files to your project resources and access them like this:
                //return Resources.IconForThisComponent;
                return null;
            }
        }

        /// <summary>
        /// Each component must have a unique Guid to identify it. 
        /// It is vital this Guid doesn't change otherwise old ghx files 
        /// that use the old ID will partially fail during loading.
        /// </summary>
        public override Guid ComponentGuid
        {
            get { return new Guid("d2e3e30d-80bb-4792-ad3f-2d8187e5ad74"); }
        }
    }
}
