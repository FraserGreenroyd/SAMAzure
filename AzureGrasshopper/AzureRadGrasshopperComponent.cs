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
    public class AzureRadGrasshopperComponent : GH_Component
    {
        /// <summary>
        /// Each implementation of GH_Component must provide a public 
        /// constructor without any arguments.
        /// Category represents the Tab in which the component will appear, 
        /// Subcategory the panel. If you use non-existing tab or panel names, 
        /// new tabs/panels will automatically be created.
        /// </summary>
        public AzureRadGrasshopperComponent()
          : base("AzureRadGrasshopper", "SAPAzure_RAD",
              "Run Radiance simulations on Azure",
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

            pManager.AddTextParameter("Sky Matrix", "Sky Matrix", "The location on your system (full file path) to the Sky Matrix JSON file", GH_ParamAccess.item);
            pManager.AddTextParameter("Surfaces", "Surfaces", "The location on your system (full file path) to the Surfaces JSON file", GH_ParamAccess.item);
            pManager.AddTextParameter("Analysis Grids", "Analysis Grids", "The location on your system (full folder path) to the analysis grids to simulate", GH_ParamAccess.item);

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

            String skyMatrix = null;
            DA.GetData(2, ref skyMatrix);
            if (skyMatrix == null)
                AddRuntimeMessage(GH_RuntimeMessageLevel.Error, "Please provide a valid Zone folder");

            if (!File.Exists(skyMatrix))
                AddRuntimeMessage(GH_RuntimeMessageLevel.Error, "Please provide a valid, existing, Zone folder");

            String surfaceJSON = null;
            DA.GetData(3, ref surfaceJSON);
            if (surfaceJSON == null)
                AddRuntimeMessage(GH_RuntimeMessageLevel.Error, "Please provide a valid Zone folder");

            if (!File.Exists(surfaceJSON))
                AddRuntimeMessage(GH_RuntimeMessageLevel.Error, "Please provide a valid, existing, Zone folder");

            /*List<String> analysisGrid = new List<string>();
            DA.GetDataList(3, folderNames);

            if (folderNames.Count == 0)
                AddRuntimeMessage(GH_RuntimeMessageLevel.Error, "Please provide a valid folder name to simulate");*/

            String analysisGridFolder = null;
            DA.GetData(4, ref analysisGridFolder);
            if (analysisGridFolder == null)
                AddRuntimeMessage(GH_RuntimeMessageLevel.Error, "Please provide a valid Analysis Grid folder location");

            if (!Directory.Exists(analysisGridFolder))
                AddRuntimeMessage(GH_RuntimeMessageLevel.Error, "Please provide a valid folder to simulate");

            bool run = false;
            DA.GetData(5, ref run);

            if (pNumber == null || pName == null || skyMatrix == null || !File.Exists(skyMatrix) || surfaceJSON == null || !File.Exists(surfaceJSON) || analysisGridFolder == null || !Directory.Exists(analysisGridFolder) || !run)
                return;

            //Everything is valid - let's run a simulation!
            AZEngine aEngine = new AZEngine(pNumber, pName);
            aEngine.CreateBlobStorage();

            //aEngine.CreateBatchClients(idfFiles.Count);
            //aEngine.CreateBatchClients(folderNames.Count);
            String[] jsonZones = Directory.GetFiles(analysisGridFolder);
            List<String> jsonZoneNames = new List<String>();
            foreach (String s in jsonZones)
                jsonZoneNames.Add(s);

            aEngine.CreateBatchClients(jsonZoneNames.Count);

            aEngine.InstallRadiance();

            while (!aEngine.TrueWhenTasksComplete())
            {
                //Wait until the install is complete...
            }

            //Upload each analysis grid
            foreach (String s in jsonZoneNames)
                aEngine.UploadFile(s);

            aEngine.UploadFile(skyMatrix);
            aEngine.UploadFile(surfaceJSON);

            while(!aEngine.TrueWhenTasksComplete())
            {
                //Wait till all have uploaded...
            }

            /*aEngine.UploadFile(epwFile);
            aEngine.UploadFiles(idfFiles);

            aEngine.RunEnergyPlus(idfFiles, epwFile);*/

            //aEngine.UploadFile(zoneFolder);

            aEngine.RunRadiance(jsonZoneNames, Path.GetFileName(skyMatrix), Path.GetFileName(surfaceJSON));

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
            get { return new Guid("B67A0E22-9EF5-4632-AE97-E0F0EEB5C328"); }
        }
    }
}
