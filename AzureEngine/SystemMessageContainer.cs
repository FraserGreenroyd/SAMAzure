using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

using System.ComponentModel; //For the INotifyProperty Interface
using System.Runtime.CompilerServices; //For the CallerMemberName

namespace AzureEngine
{
    public class SystemMessageContainer : INotifyPropertyChanged
    {
        #region Variables
        public event PropertyChangedEventHandler PropertyChanged;
        public event PropertyChangedEventHandler MessagesUpdated;

        private List<SystemMessage> messages;
        #endregion

        #region Constructors
        public SystemMessageContainer()
        {
            messages = new List<SystemMessage>();
        }
        #endregion

        #region Functions
        public void AddMessage(String message)
        {
            messages.Add(new SystemMessage(message));
            NotifyMessagesChanged();
        }

        public void AddMessage(String message, SystemMessage.MessageType type)
        {
            messages.Add(new SystemMessage(message, type));
            NotifyMessagesChanged();
        }

        public void AddMessage(String message, SystemMessage.MessageType type, String errorDetails)
        {
            messages.Add(new SystemMessage(message, type, errorDetails));
            NotifyMessagesChanged();
        }

        public void AddInformationMessage(String message)
        {
            AddMessage(message, SystemMessage.MessageType.Information);
        }

        public void AddWarningMessage(String message)
        {
            AddMessage(message, SystemMessage.MessageType.Warning);
        }

        public void AddErrorMessage(String message)
        {
            AddMessage(message, SystemMessage.MessageType.Error);
        }

        public void AddErrorMessage(String message, String errorDetails)
        {
            AddMessage(message, SystemMessage.MessageType.Error, errorDetails);
        }
        #endregion

        #region Events
        private void NotifyMessagesChanged([CallerMemberName] String propertyName = "")
        {
            if (MessagesUpdated != null)
                MessagesUpdated(this, new PropertyChangedEventArgs(propertyName));
        }
        #endregion
    }
}
