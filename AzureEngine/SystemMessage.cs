/*
 * This class is for the structure of messages raised by the AzureEngine.
 * These could include messages relating to the status of operations, or warning and error messages
 * Author: F. Greenroyd
 * Date: 2018-06-20 
 */

using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace AzureEngine
{
    public class SystemMessage
    {
        #region Enums
        public enum MessageType { Unknown, Status, Information, Warning, Error };
        #endregion

        #region Variables
        private DateTime messageTimeStamp;
        private String message;
        private MessageType messageType;
        private String errorDetails; //Not used in all messages - will be used when throwing exceptions mostly for Debug and Reporting purposes
        #endregion

        #region Constructors
        /// <summary>
        /// Empty constructor with a new message instance
        /// </summary>
        public SystemMessage()
        {
            message = "";
            messageType = MessageType.Unknown;
            messageTimeStamp = DateTime.Now;
        }

        /// <summary>
        /// Create a new system message instance with a message to display to the user
        /// </summary>
        /// <param name="message">String - the message to display to the user</param>
        public SystemMessage(String message)
        {
            this.message = message;
            messageType = MessageType.Unknown;
            messageTimeStamp = DateTime.Now;
        }

        /// <summary>
        /// Create a new system message instance of a specified type
        /// </summary>
        /// <param name="message">String - the message to display to the user</param>
        /// <param name="type">Enum - what type of message is this? Options: Status, Information, Warning, Error</param>
        public SystemMessage(String message, MessageType type)
        {
            this.message = message;
            messageType = type;
            messageTimeStamp = DateTime.Now;
        }

        /// <summary>
        /// Create a new system message instance of a specified type
        /// </summary>
        /// <param name="message">String - the message to display to the user</param>
        /// <param name="type">Enum - what type of message is this? Options: Status, Information, Warning, Error</param>
        /// <param name="errorDetails">String - additional error details to display to the user</param>
        public SystemMessage(String message, MessageType type, String errorDetails)
        {
            this.message = message;
            messageType = type;
            messageTimeStamp = DateTime.Now;
            this.errorDetails = errorDetails;
        }
        #endregion

        #region Properties
        public DateTime TimeStamp
        {
            get { return messageTimeStamp; } //Read only property - no option to set the DateTime
        }

        public String Message
        {
            get { return message; }
            set { message = value; }
        }

        public MessageType Type
        {
            get { return messageType; }
            set { messageType = value; }
        }

        public String ErrorDetails
        {
            get { return errorDetails; }
            set { errorDetails = value; }
        }
        #endregion
    }
}
