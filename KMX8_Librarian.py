# KMX-8 Librarian
# Copyright (c)2021 Dan Higdon
# Inspired by Atari ST librarian shipped with the KMX-8

import tkinter as tk
import json

chr_ht=25

# Configuration data file is a dictionary with the following entries
# inputs    : list of 8 input names
# outputs   : list of 8 output names
# patches   : list of
#   name : string
#   routing : list of 8 integers. 0 = "none", 1-8 = channel, 9 = merged
# NOTE - input/output devices are not part of the patch because it's
# not easy to swap the physical cables around.

# Patch numbers are discontinuous
valid_patches = list(range(1,9)) + list(range(10,19)) + list(range(20,29))

# Connection range - the KMX-8 has 8 possible connection inputs and outputs
con_range = range(0,8)

configuration = {
    'inputs' : [ 'PC','SQ-1+32','NordLead','Unused', 'ESI-32','DR-660','KeyStep','Wally'],
    'outputs' : [ 'PC','SQ-1+32','NordLead','MicroBrute', 'ESI-32','DR-660','KeyStep','Wally' ],
    }

# initial patches. Note that some of these patches aren't actually addressable
# by the KMX-8
patches = [ { 'name' : ('Patch #' + str(i+1)),
              'routing': [ 0 for j in con_range ] }
        for i in range(0,30) ]

class LibrarianFrame(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.master = master

        # Start with all outputs connected to nothing
        self.edit_patch = 0
        self.routing = [0 for i in con_range]
        self.lines = [None for i in con_range] 

        master.columnconfigure(1,weight=1)

        # Set the master's size and title bar
        master.title("KMX-8 Librarian")
        master.geometry('400x320')

        # Create the functional regions of the UI and populate them
        # with controls.
        self.patch_frame = tk.Frame(master)
        self.create_patch_select(self.patch_frame)
        self.patch_frame.grid(column=0,row=0)

        self.patchbay_frame = tk.Frame(master)
        self.create_patchbay(self.patchbay_frame)
        self.patchbay_frame.grid(column=0,row=1)

        self.button_frame = tk.Frame(master)
        self.create_buttons(self.button_frame)
        self.button_frame.grid(column=1,row=0,stick="e",rowspan=2)

    # Tracking the current patch
    def create_patch_select(self,master):
        self.identification = tk.Label(master,text='ENSONIQ // KMX 8 Remote', fg='white',bg='black')
        self.copyright = tk.Label(master,text='Copyright (c)2021 Dan Higdon.\nAll Rights Reserved')
        self.patch_select = tk.Spinbox(master,values=valid_patches, command=self.do_change_patch)
        self.patch_name = tk.Label(master)

        self.identification.pack(side='top',fill='x')
        self.copyright.pack(side='top',fill='x')
        self.patch_select.pack(side='left')
        self.patch_name.pack(side='left',expand=True,fill='x')

        self.do_change_patch() # populates patch name from patch_select

    # Create the controls that drive the patch bay
    def create_patchbay(self,master):
        self.input_index = tk.IntVar()
        self.input_labels = [tk.Label(master,text=configuration['inputs'][i]) for i in con_range]
        self.input_buttons = [
                tk.Radiobutton(master,
                    text=str(i+1),
                    value=i,
                    variable=self.input_index)
                for i in con_range]
        self.output_labels = [tk.Label(master,text=configuration['outputs'][i]) for i in con_range]
        self.output_buttons = [
                tk.Button(master,
                    text=str(i+1),
                    command=self.do_output_button(i))
                for i in con_range]
        self.canvas = tk.Canvas(master, width=80, height=chr_ht*8)

        self.in_label=tk.Label(master,text='IN')
        self.out_label=tk.Label(master,text='OUT')

        # Place them in the grid
        self.in_label.grid(row=0,column=1)
        self.out_label.grid(row=0,column=3)
        self.canvas.grid(row=1,column=2,rowspan=8)
        for r in con_range:
            self.input_labels[r].grid(row=r+1,column=0,sticky="w") 
            self.input_buttons[r].grid(row=r+1,column=1,sticky="w")
            self.output_buttons[r].grid(row=r+1,column=3,sticky="e")
            self.output_labels[r].grid(row=r+1,column=4,sticky="w") 

        # Finally, draw the connections
        self.create_connections()
        self.update_connections()

    # Create the buttons that run the editor's functions
    def create_buttons(self, master):
        tk.Label(master,text='KMX8->PC').pack(fill='x')
        self.get_patches = tk.Button(master,text='Get Patches',command=self.do_get_patches)
        self.get_patches.pack(fill='x')

        tk.Label(master,text='KMX8<-PC').pack(fill='x')
        self.send_patches = tk.Button(master,text='Send Patches',command=self.do_send_patches)
        self.send_patches.pack(fill='x')

        tk.Label(master,text='Edit').pack(fill='x')
        self.send_patches = tk.Button(master,text='Send Patches',command=self.do_send_patches)
        self.copy_patch = tk.Button(master,text='Copy',command=self.do_edit_copy)
        self.copy_patch.pack(fill='x')

        self.paste_patch = tk.Button(master, text='Paste', command=self.do_edit_paste)
        self.paste_patch.pack(fill='x')

        tk.Label(master,text='Disk File').pack(fill='x')
        self.load_patches = tk.Button(master,text='Load',command=self.do_disk_load)
        self.load_patches.pack(fill='x')

        self.save_patches = tk.Button(master,text='Save',command=self.do_disk_save)
        self.save_patches.pack(fill='x')

        self.save_config = tk.Button(master,text='Save CNFG',command=self.do_disk_save_config)
        self.save_config.pack(fill='x')

    # Return Y coordinate of the given routing slot
    def get_y(self,slot):
        return slot * chr_ht + chr_ht/2

    def create_connections(self):
        self.lines = [None for i in con_range]

    def update_connections(self):
        for out in con_range:
            self.update_connection(out)

    def update_connection(self,out):
        id = self.lines[out]
        # Routing 0 is "no connection".
        # Routing 9 is "merged connection"
        if self.routing[out] == 0:
            # no connection, delete the line if it exists
            if id != None:
                self.canvas.delete(id)
                id = None 
                self.lines[out] = id
        else:
            # Make sure the connection line exists
            if id == None:
                id = self.canvas.create_line(0,0,80,0)
                self.lines[out] = id

        # If we have a connection to this output, make sure
        # that its connected to the right input
        if id != None:
            from_y = self.get_y(self.routing[out]-1)
            to_y = self.get_y(out)
            self.canvas.coords(self.lines[out],0,from_y,80,to_y)


    # Patch Select
    # Saves edit buffer into current patch slot, then loads the new patch
    def do_change_patch(self):
        pn = int(self.patch_select.get())-1
        patch = patches[pn]
        if self.edit_patch != pn:
            old_patch = patches[self.edit_patch]
            for i in con_range:
                old_patch['routing'][i] = self.routing[i]
                self.routing[i] = patch['routing'][i]
                self.update_connection(i)
            self.edit_patch = pn
        self.patch_name['text'] = patch['name']


    # Curried for ease of implementation
    def do_output_button(self, index):
        def internal():
            # toggle the routing
            src = self.input_index.get()+1
            if self.routing[index] != src:
                self.routing[index] = src
            else:
                self.routing[index] = 0;
            self.update_connection(index)
        return internal

    # Buttons
    def do_get_patches(self):
        print("TODO: get patches")

    def do_send_patches(self):
        print("TODO: send patches")

    def do_edit_copy(self):
        print("TODO: edit copy")

    def do_edit_paste(self):
        print("TODO: edit paste")

    def do_disk_load(self):
        print("TODO: disk load")

    def do_disk_save(self):
        print("TODO: disk save")
        print(json.dumps(patches))

    def do_disk_save_config(self):
        print("TODO: disk save configuration")
        print(json.dumps(configuration,indent=2))

# Create the appliation
def main():
    app = LibrarianFrame(tk.Tk())
    app.mainloop()

if __name__ == '__main__':
    main()
