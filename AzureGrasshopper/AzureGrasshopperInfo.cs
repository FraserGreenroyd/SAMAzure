using System;
using System.Drawing;
using Grasshopper.Kernel;

namespace AzureGrasshopper
{
    public class AzureGrasshopperInfo : GH_AssemblyInfo
    {
        public override string Name
        {
            get
            {
                return "AzureGrasshopper";
            }
        }
        public override Bitmap Icon
        {
            get
            {
                //Return a 24x24 pixel bitmap to represent this GHA library.
                return null;
            }
        }
        public override string Description
        {
            get
            {
                //Return a short string describing the purpose of this GHA library.
                return "";
            }
        }
        public override Guid Id
        {
            get
            {
                return new Guid("5aaf6e99-1021-48de-8737-d8ee90a187ec");
            }
        }

        public override string AuthorName
        {
            get
            {
                //Return a string identifying you or your company.
                return "";
            }
        }
        public override string AuthorContact
        {
            get
            {
                //Return a string representing your preferred contact details.
                return "";
            }
        }
    }
}
