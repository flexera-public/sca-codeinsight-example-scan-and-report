'''
Copyright 2021 Flexera Software LLC
See LICENSE.TXT for full license text
SPDX-License-Identifier: MIT

Author : sgeary  
Created On : Fri Sep 24 2021
File : scan_and_report.py
'''
import requests
import logging
import time
import sys
import zipfile
import io


logfileName = "_scan_and_report.log"

###################################################################################
#  Set up logging handler to allow for different levels of logging to be capture
logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s', datefmt='%Y-%m-%d:%H:%M:%S', filename=logfileName, filemode='w',level=logging.DEBUG)
logger = logging.getLogger(__name__)

#----------------------------------------------------------------------#
def main():
    projectName = (sys.argv[1])
    reportName = (sys.argv[2])

  
    authToken = "eyJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJzZ2VhcnkiLCJ1c2VySWQiOjksImlhdCI6MTYyOTQwMTAzM30._NyOGbk1m0hp_tJpfUNiUQAkxPBSM22DSKeTYLR-QUmZAVkbXwHOckosrc1bk5Oqfe1aRwhkhmqPECmBxCsLnw"
    codeInsightURL = "http://localhost:8888"


    projectID = get_projectID(projectName, codeInsightURL, authToken)
    if not projectID:
        print("No project found")
        sys.exit(-1)

    reportID = get_reportID(reportName, codeInsightURL, authToken)
    if not reportID:
        print("No report found")
        sys.exit(-1)

    # Initiate a Scan
    scanID = scan_project(projectID, codeInsightURL, authToken)
    logger.debug("Project scan started with scan ID %s" %scanID)
    print("Project scan started with scan ID %s" %scanID)

 # Query the scan until it completes
    
    scanStatus = get_scan_status(scanID, codeInsightURL, authToken)
    
    while scanStatus not in ["completed", "terminated", "failed"]:
        logger.debug("in while loop %s" %scanStatus)
        #  See if it is schedule at this point.. If so hold here in a loop until it is active
        if scanStatus in ["scheduled", "waiting on update"]:
            
            print("Project queued for scanning", end = '', flush=True)
      
            # Loop around while the scan is pending
            while scanStatus in ["scheduled", "waiting on update"]:
                logger.debug("While loop - Scan Status is now %s" %scanStatus)
              
                # Check the status every 10 seconds  * 5*2   
                for x in range(5):
                    time.sleep(2)                    
                    # But update the window every 2 seconds 
                    if x == 4:         
                        scanStatus = get_scan_status(scanID, codeInsightURL, authToken)
                        logger.debug("Scan Status is now %s" %scanStatus)
                        print(".", end = '', flush=True)
            print("")
                                
            print("Project preparing to be scanned.")
            
        #  After it was scheduled it should not be active so start to loop here
        if scanStatus == "active":
            print("Scanning project", end = "", flush=True)
           
            # Loop around while the scan is happening
            while scanStatus == "active":
               
                # But update the window every 2 seconds    
                for x in range(5):
                    time.sleep(5)
                    print(".", end ="", flush=True)
                    
                    # Check the status every 25 seconds  * 5*5
                    if x == 4:         
                        scanStatus = get_scan_status(scanID, codeInsightURL, authToken)
                        logger.debug("scanStatus:  %s" %scanStatus)

        # Get an update on the status
        scanStatus = get_scan_status(scanID, codeInsightURL, authToken)
    
    if scanStatus != "completed":
        print("Scan was not successful")
        sys.exit(-1)
    else:
        logger.debug("Project scan completed with status %s" %scanStatus)
        print("Project scan completed with status %s" %scanStatus)


    # Now that the scan has completed

    reportTaskID = generate_report(projectID, reportID, codeInsightURL, authToken)

    reportZipFile = download_report(projectID, reportID, reportTaskID, codeInsightURL, authToken)

    # Open the zip file and create the individual reports files
    with zipfile.ZipFile(io.BytesIO(reportZipFile)) as zipFileContents:
        zipFileContents.extractall("codeinsight-reports")
            
 
###############################################################################################################
#--------------------------------------------------
def get_projectID(projectName, codeInsightURL, authToken):

    apiEndPoint = codeInsightURL + "/codeinsight/api/project/id"
    apiEndPoint += "/?projectName=" + projectName
  
    logger.debug("    apiEndPoint: %s" %apiEndPoint)
    headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + authToken} 
    
    #  Make the request to get the required data   
    try:
        response = requests.get(apiEndPoint, headers=headers)
    except requests.exceptions.RequestException as error:  # Just catch all errors
        logger.error(error)
        return

    ###############################################################################
    # We at least received a response from Code Insight so check the status to see
    # what happened if there was an error or the expected data
    if response.status_code == 200:
        projectID = response.json()["Content: "]
        logger.debug("%s has a corresponding project ID or: %s" %(projectName, projectID))
        return projectID
    else:
        logger.error(response.text)
        return 


#--------------------------------------------------
def get_reportID(reportName, codeInsightURL, authToken):

    apiEndPoint = codeInsightURL + "/codeinsight/api/reports"

    logger.debug("    apiEndPoint: %s" %apiEndPoint)
    headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + authToken} 
    
    #  Make the request to get the required data   
    try:
        response = requests.get(apiEndPoint, headers=headers)
    except requests.exceptions.RequestException as error:  # Just catch all errors
        logger.error(error)
        return

    ###############################################################################
    # We at least received a response from Code Insight so check the status to see
    # what happened if there was an error or the expected data
    if response.status_code == 200:
        reports = response.json()["data"]

        for report in reports:
            if report["name"] == reportName:
                logger.debug("%s has a corresponding report ID or: %s" %(reportName, report["id"]))
                return report["id"]
        # No report with that name found
        logger.error("No report with the name %s found" %reportName)
        return False

    else:
        logger.error(response.text)
        return 


#--------------------------------------------------
def scan_project(projectID, codeInsightURL, authToken):

    apiEndPoint = codeInsightURL + "/codeinsight/api/scanResource/projectScan"
    apiEndPoint += "/" + str(projectID)
  
    logger.debug("    apiEndPoint: %s" %apiEndPoint)
    headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + authToken} 
    
    #  Make the request to get the required data   
    try:
        response = requests.post(apiEndPoint, headers=headers)
    except requests.exceptions.RequestException as error:  # Just catch all errors
        logger.error(error)
        return

    ###############################################################################
    # We at least received a response from Code Insight so check the status to see
    # what happened if there was an error or the expected data
    if response.status_code == 200:
        scanID = response.json()["Content: "]
        logger.debug("Scan started with ID: %s" %scanID)
        return scanID
    else:
        logger.error(response.text)
        return 


#--------------------------------------------------
def get_scan_status(scanID, codeInsightURL, authToken):

    apiEndPoint = codeInsightURL + "/codeinsight/api/project/scanStatus"
    apiEndPoint += "/" + str(scanID)
  
    logger.debug("    apiEndPoint: %s" %apiEndPoint)
    headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + authToken} 
    
    #  Make the request to get the required data   
    try:
        response = requests.get(apiEndPoint, headers=headers)
    except requests.exceptions.RequestException as error:  # Just catch all errors
        logger.error(error)
        return

    ###############################################################################
    # We at least received a response from Code Insight so check the status to see
    # what happened if there was an error or the expected data
    if response.status_code == 200:
        scanState = response.json()["Content: "]
        logger.debug("Returning Scan State: %s" %scanState)
        return scanState
    else:
        logger.error(response.text)
        return 


#--------------------------------------------------
def generate_report(projectID,  reportID, codeInsightURL, authToken):

    apiEndPoint = codeInsightURL + "/codeinsight/api/projects"
    apiEndPoint += "/" + str(projectID)
    apiEndPoint += "/reports/" + str(reportID)
    apiEndPoint += "/generate"
  
    logger.debug("    apiEndPoint: %s" %apiEndPoint)
    headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + authToken} 
    
    #  Make the request to get the required data   
    try:
        response = requests.post(apiEndPoint, headers=headers)
    except requests.exceptions.RequestException as error:  # Just catch all errors
        logger.error(error)
        return

    ###############################################################################
    # We at least received a response from Code Insight so check the status to see
    # what happened if there was an error or the expected data
    if response.status_code == 200:
        taskID = response.json()["data"]["taskId"]
        logger.debug("Report generated with task ID: %s" %taskID)
        return taskID
    else:
        logger.error(response.text)
        return 

#--------------------------------------------------
def generate_report(projectID,  reportID, codeInsightURL, authToken):

    apiEndPoint = codeInsightURL + "/codeinsight/api/projects"
    apiEndPoint += "/" + str(projectID)
    apiEndPoint += "/reports/" + str(reportID)
    apiEndPoint += "/generate"
    logger.debug("    apiEndPoint: %s" %apiEndPoint)

    reportOptions = '''{
                            "options": {
                                "includeChildProjects": "false",
                                "includeComplianceInformation": "false",
                                "maxVersionsBack": "10",
                                "cvssVersion": "3.0"
                            }
                        }'''
    headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + authToken} 
    
    #  Make the request to get the required data   
    try:
        response = requests.post(apiEndPoint, headers=headers, data=reportOptions)
    except requests.exceptions.RequestException as error:  # Just catch all errors
        logger.error(error)
        return

    ###############################################################################
    # We at least received a response from Code Insight so check the status to see
    # what happened if there was an error or the expected data
    if response.status_code == 200:
        taskID = response.json()["data"]["taskId"]
        logger.debug("Report generated with task ID: %s" %taskID)
        return taskID
    else:
        logger.error(response.text)
        return 


#--------------------------------------------------
def download_report(projectID,  reportID, taskID, codeInsightURL, authToken):

    apiEndPoint = codeInsightURL + "/codeinsight/api/projects"
    apiEndPoint += "/" + str(projectID)
    apiEndPoint += "/reports/" + str(reportID)
    apiEndPoint += "/download?taskId=" + str(taskID)
  
    logger.debug("    apiEndPoint: %s" %apiEndPoint)
    headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + authToken} 
    
    #  Make the request to get the required data   
    try:
        response = requests.get(apiEndPoint, headers=headers)
    except requests.exceptions.RequestException as error:  # Just catch all errors
        logger.error(error)
        return

    ###############################################################################
    # We at least received a response from Code Insight so check the status to see
    # what happened if there was an error or the expected data

    while response.status_code == 202:
        logger.info("Report generation in process")
        print("Report generation in process")
        time.sleep(5)
        response = requests.get(apiEndPoint, headers=headers)
        

    if response.status_code == 200:
        # The report has completed
        logger.info("Report has been generated")
        print("Report has been generated")
        reportZipFile = response.content        
        return reportZipFile

    else:
        logger.error(response.text)
        return 





###########################################################################  
if __name__ == "__main__":
    main()  