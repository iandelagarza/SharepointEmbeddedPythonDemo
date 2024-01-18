import json
import requests
from requests import Response
from GetAuthorizationToken import TokenGetter
from pick import pick 
from enum import Enum
import numpy as np
JSON_PATH = './Values.json'
    
def getJson() -> json:
    with open(JSON_PATH) as json_file:
        data = json.load(json_file)
        return data
    
#create an enum
class Method(Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"
    TRACE = "TRACE"
    CONNECT = "CONNECT"

class State(str, Enum):
    START = "start"
    SELECT_CONTAINER = "Select Container"
    CREATE_CONTAINER = "Create Container"
    DELETE_CONTAINER = "Delete Container"
    RETURN = "Return"

class ContainerState(str, Enum):
    START = "start"
    VIEW_DIRECTORY = "View Raw Contents"
    VIEW_FILES_AND_FOLDERS = "View Files and Folders"
    CREATE_FILE = "Create File"
    CREATE_FOLDER = "Create Folder"
    DELETE_FILE_FOLDER = "Delete File or Folder"
    OPEN_FILE_FOLDER = "Open File or Folder"
    RETURN = "Return"
    EXIT = "Exit"

class MenuState(str, Enum):
    START = "start"
    SELECT_CONTAINER_TYPE = "Select Container Type"
    EXIT = "Exit"

class ContainerTypes(str, Enum):
    ContainerAppData = "ContainerApp"

class Container:
    def __init__(self):
        self.Name = None
        self.Id = None
       
class Root:
    #dictionary of folders
    def __init__(self):
        self.root = []
        
    def add_folder(self, folderName: str, folderId: str):
        self.root.append([folderName, folderId])
        
    def pop_folder(self):
        if (len(self.root) >= 1):
            self.root.pop()
            return True
        return False
        
    def get_root_path(self):
        #return root path as string
        if (len(self.root) < 1):
            return "root"
        string = ""
        for folder in self.root:
            string += folder[0] + "/"
        if  (string == ""):
            string =  "root"
        return string
    def get_root_id(self):
        #return root path as string
        if (len(self.root) < 1):
            return "root"
        return self.root[-1][1]
        
class Application():
    def __init__(self, data:json):
        self.__data = data
        self.tenantData = data["TenantData"]
        self.selectedContainer = Container()
        self.__token = None
        self.root = Root()
        pass       
        
    def get_token(self, tenantData : json):
        tokenGetter = TokenGetter(tenantData["TenantId"])
        self.__token = tokenGetter.get_token(self.appData, ".default")
    
    def send_request(self, url: str, method: Method, body: json = None, params: json = None, data: json = None) -> Response:
        if (self.__token is None):
            print("No Token")
            return
        
        headers = {'Authorization': 'Bearer ' + self.__token}
        if (method == Method.GET):
            response = requests.get(url, headers=headers, params=params, json=body, data=data)
        elif (method == Method.POST):
            response = requests.post(url, headers=headers, params=params, json=body, data=data)
        elif (method == Method.PUT):
            response = requests.put(url, headers=headers, params=params, json=body, data=data)
        elif (method == Method.DELETE):
            response = requests.delete(url, headers=headers, params=params, json=body, data=data)
        
        if (response.status_code < 400):
            if(response.text == ""):
                return Response()
            return response
        else:
            #print(json.dumps(response.json(), indent=4, sort_keys=True))
            print(response.status_code)
            print(response.text)
        return Response()
        
    def start(self)->str:
        options = [state.value for state in State ]
        value, _ = pick(options[1:], f"Choose an option", indicator="=>")
        return value

    def select_container(self):
        params = {'$filter': f'containerTypeId eq {self.appData["ContainerTypeId"]}'}

        response = self.send_request('https://graph.microsoft.com/beta/storage/fileStorage/containers', Method.GET, params=params).json()
        containerNames = [container["displayName"] for container in response["value"]]
        value, index = pick(containerNames, "Select a container", indicator="=>")
        self.selectedContainer.Name = value
        return value, response["value"][index]["id"]
    
    def set_container_values(self, name, id):
        self.selectedContainer.Name = name
        self.selectedContainer.Id = id

    def create_container(self):
        #clear terminal
        print("\033c")
        body = {
            "displayName": input("Enter Container Name: "),
            "containerTypeId": self.appData["ContainerTypeId"],
            "description": input("Enter Container Description: ")
        }
        response = self.send_request('https://graph.microsoft.com/beta/storage/fileStorage/containers', Method.POST, body).json()
        self.selectedContainer.Name = response["displayName"]
        self.selectedContainer.Id = response["id"]
        self.send_request(f'https://graph.microsoft.com/beta/storage/fileStorage/containers/{self.selectedContainer.Id}/activate', Method.POST)

    def delete_container(self, name, id):
        #clear terminal
        #
        print("\033c")
        if (name is None or id is None):
            input("No Container Selected\nPress Enter to Continue...")
            return
        if (input(f"Are you sure you want to delete {name}? (y/n)") != "y"):
            return
        self.send_request(f'https://graph.microsoft.com/beta/storage/fileStorage/containers/{id}', Method.DELETE)
        self.selectedContainer = Container()
        
    def container_start(self):
        options = [state.value for state in ContainerState ]
        value, _ = pick(options[1:], f"Container selected: {self.selectedContainer.Name} \nRoot:{self.root.get_root_path()}", indicator="=>")
        return value
    
    def view_directory(self, silence : bool = False) -> json:
        root = self.root.get_root_id()
        url = f"https://graph.microsoft.com/v1.0/drives/{self.selectedContainer.Id}/items/{root}/children"
        print(url)
        response = self.send_request(url, Method.GET).json()
        if (not silence):
            print(json.dumps(response, indent=4, sort_keys=True))
            input("Press Enter to Continue...")
        return response

    def create_file(self):
        print("\033c")
        root = self.root.get_root_id()
        file_name = f"{input('File Name:')}.txt"
        content = input("File Contents:")
        data = content.encode("utf-8")
        url = f"https://graph.microsoft.com/v1.0/drives/{self.selectedContainer.Id}/items/{root}:/{file_name}:/content"

        response = self.send_request(url, method=Method.PUT, data=data)
        if response.status_code == 201:
            print("File created and uploaded successfully.")
        else:
            print("Failed to create and upload file.")

        input("Press Enter to Continue...")

    def create_folder(self):
        print("\033c")
        root = self.root.get_root_id()
        folder_name = input("Folder Name:")
        url = f"https://graph.microsoft.com/v1.0/drives/{self.selectedContainer.Id}/items/{root}/children"

        response = self.send_request(url, method=Method.POST, body={"name": folder_name, "folder": {}})
        id = response.json()["id"]
        self.root.add_folder(folder_name, id)
        if response.status_code == 201:
            print("Folder created successfully.")
        else:
            print("Failed to create folder.")

        input("Press Enter to Continue...")

    def open_file(self, response: json):
        resp = self.send_request(response["@microsoft.graph.downloadUrl"], Method.GET)
        print(resp.content.decode())
        input("Press Enter to Continue...")
    
    def open_folder(self, response: json):
        self.root.add_folder(response["name"], response["id"])

    def select_file_or_folder(self) -> (str, json):
        contents = self.view_directory(True)
        if (contents is None):
            print("No Contents")
            input("Press Enter to Continue...")
            return None, None  # Return early when contents is None
        
        options = np.array([[content["name"],content["id"]]for content in contents["value"]])
        if len(options) == 0:
            print("No Files or Folders")
            input("Press Enter to Continue...")
            return None, None  # Return early when options is empty
        
        value, index = pick(options[:,0].tolist(), f"Choose an option", indicator="=>")
        id = options[index][1]
        print("\033c")
        return value, id
        
    def open_file_or_folder(self):
        value, id = self.select_file_or_folder()
        if value is None or id is None:
            return  # Return early when value or id is None
        url = f"https://graph.microsoft.com/v1.0/drives/{self.selectedContainer.Id}/items/{id}"
        response = self.send_request(url, Method.GET).json()
        if (str(value).endswith(".txt")):
            self.open_file(response)
        else:
            self.open_folder(response)
            
    def delete_file_or_folder(self):
        value, id = self.select_file_or_folder()
        if value is None or id is None:
            return  # Return early when value or id is None
        url = f"https://graph.microsoft.com/v1.0/drives/{self.selectedContainer.Id}/items/{id}"
        response = self.send_request(url, Method.DELETE)
        print(response.status_code)
        print(response.text)
        input("Press Enter to Continue...")
                
    def run_container_actions(self):
        containerState = ContainerState.START
        while (containerState != ContainerState.EXIT):
            print("\033c")
            if (containerState == ContainerState.START):
                containerState = self.container_start()
            elif (containerState == ContainerState.VIEW_DIRECTORY):
                self.view_directory()
                containerState = ContainerState.START
            elif (containerState == ContainerState.VIEW_FILES_AND_FOLDERS):
                contents = self.view_directory(True)
                array = np.array([[content["name"],content["id"]]for content in contents["value"]]).tolist()
                if(len(array) == 0):
                    print("No Files or Folders")
                else:
                    print(array)
                input("Press Enter to Continue...")
                containerState = ContainerState.START
            elif (containerState == ContainerState.CREATE_FILE):
                self.create_file()
                containerState = ContainerState.START
            elif (containerState == ContainerState.CREATE_FOLDER):
                self.create_folder()
                containerState = ContainerState.START
            elif (containerState == ContainerState.OPEN_FILE_FOLDER):
                self.open_file_or_folder()
                containerState = ContainerState.START
            elif (containerState == ContainerState.DELETE_FILE_FOLDER):
                self.delete_file_or_folder()
                containerState = ContainerState.START
            elif (containerState == ContainerState.RETURN):
                if self.root.pop_folder():
                    containerState = ContainerState.START
                else:
                    containerState = ContainerState.EXIT
            else:
                print("Invalid State")
                containerState = ContainerState.EXIT
    
    def run_container_selection(self):
        self.get_token(self.tenantData)
        state = State.START
        while (state != State.RETURN):
            print("\033c")
            if (state == State.START):
                state = self.start()
            elif (state == State.SELECT_CONTAINER):
                self.set_container_values(*self.select_container())
                self.run_container_actions()
                state = State.START
            elif (state == State.CREATE_CONTAINER):
                self.create_container()
                self.run_container_actions()
                state = State.START
            elif (state == State.DELETE_CONTAINER):
                self.delete_container(*self.select_container())
                state = State.RETURN
            elif (state == State.RETURN):
                if self.root.pop_folder():
                    state = State.START
            else:
                print("Invalid State")
                state = State.RETURN

    def start_menu_select(self):
        options = [state.value for state in MenuState ]
        value, _ = pick(options[1:], f"Choose an option", indicator="=>")
        return value
    
    def select_container_type(self):
        options = [containerType.value for containerType in ContainerTypes]
        value, _ = pick(options, f"Choose an option", indicator="=>")
        self.appData = self.__data["ContainerTypes"][ContainerTypes(value).name]
    
    def run(self):
        state = MenuState.START
        while (state != MenuState.EXIT):
            print("\033c")
            if (state == MenuState.START):
                state = self.start_menu_select()
            elif (state == MenuState.SELECT_CONTAINER_TYPE):
                self.select_container_type()
                self.run_container_selection()
                state = MenuState.START
            elif (state == MenuState.EXIT):
                print("Exit")
            else:
                print("Invalid State")
                state = MenuState.EXIT
                
                
if (__name__ == "__main__"):
    #Open Json File
    app = Application(getJson())
    app.run()
    pass