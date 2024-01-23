import os
import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

from process_logfile import database_entry
from create_database import fibre_database
from pos import *
os.chdir(r'/home/pos_eng/WEAVE/fstest')
import FSTest as fs
from astropy.stats import sigma_clip
import bottleneck as bn

ID = np.arange(0, 1009).astype(list)
ID = list(ID)

moveslist = ['moves', 'unparks', 'parks']

###To do:
#Scrub 20221212.log and re-run once its rolled over to next logfile to pick up all the recent movements


class offset_calc():

    def __init__(self, id_list=ID, backup=False):
        assert type(id_list)==list or type(id_list)==int, 'Fibre ids must be entered as a list or a single integer'
        self.ids = id_list
        self.fd = fibre_database(backup=backup)

        print('Database connection established')
        return


    def calculate_offset(self, move_type, plate, robot, sigmaclip=True):
        tbles = ['moves', 'parks', 'unparks']
        assert type(move_type)==str, 'move_type must be entered as a string'
        assert move_type in tbles, 'move_type must either be moves, unparks, or parks'
        if type(self.ids)==list:
            self.mean_offsets = []
            for index, item in enumerate(self.ids):
                self.dx = []
                self.dy = []
                entries = self.fd.check_entries(item, move_type, plate=plate, robot=robot)
                if not entries:
                    continue
                for j in entries:
                    X = j[12] - j[10] #np.abs(j[10]) - np.abs(j[12])
                    Y = j[13] - j[11] #np.abs(j[11]) - np.abs(j[13])
                    self.dx.append(X)
                    self.dy.append(Y)
                #putting in sigma clipping here
                if not self.dx or not self.dy:
                    print('trigger', item)
                    continue
                if sigmaclip:
                    clip1_x = sigma_clip(self.dx, sigma=3, maxiters=5)
                    clip1_y = sigma_clip(self.dy, sigma=3, maxiters=5)

                    clip2_x = sigma_clip(clip1_x, sigma=1.5, maxiters=5)
                    clip2_y = sigma_clip(clip1_y, sigma=1.5, maxiters=5)
                    if len(clip2_x)<50:
                        self.mean_offsets.append([item, -np.mean(clip2_x), -np.mean(clip2_y)])
                    else:
                        mean_roll_x = bn.move_mean(clip2_x, window=50)
                        mean_roll_y = bn.move_mean(clip2_y, window=50)
                        self.mean_offsets.append([item, -mean_roll_x[-1], mean_roll_y[-1]])
                    #self.mean_offsets.append([item, -np.mean(sigma_clip(self.dx, sigma=3, maxiters=iter)), -np.mean(sigma_clip(self.dy, sigma=3, maxiters=iter))])
                else:
                    self.mean_offsets.append([item, -np.mean(self.dx), -np.mean(self.dy)])
            return self.mean_offsets
        entries = self.fd.check_entries(self.ids, move_type, plate=plate, robot=robot)
        if not entries:
            return self.mean_offsets
        self.dx = []
        self.dy = []
        for j in entries:
            X = np.abs(j[10]) - np.abs(j[12])
            Y = np.abs(j[11]) - np.abs(j[13])
            self.dx.append(X)
            self.dy.append(Y)
        if sigmaclip:

            clip1_x = sigma_clip(self.dx, sigma=3, maxiters=5)
            clip1_y = sigma_clip(self.dy, sigma=3, maxiters=5)

            clip2_x = sigma_clip(clip1_x, sigma=1.5, maxiters=5)
            clip2_y = sigma_clip(clip1_y, sigma=1.5, maxiters=5)

            if len(self.dx)<50:

                self.mean_offsets.append([self.ids, -np.mean(clip2_x), -np.mean(clip2_y)])
            else:
                mean_roll_x = bn.move_mean(clip2_x, window=50)
                mean_roll_y = bn.move_mean(clip2_y, window=50)
                self.mean_offsets.append([self.ids, -mean_roll_x[-1], mean_roll_y[-1]])
            #self.mean_offsets.append([self.ids, -np.mean(sigma_clip(self.dx, sigma=3, maxiters=iter)), -np.mean(sigma_clip(self.dy, sigma=3, maxiters=iter))])
        else:
            self.mean_offsets.append([self.ids, -np.mean(self.dx), -np.mean(self.dy)])
        return self.mean_offsets


    def calculate_All_fibre_offsets(self, p, r, sigmaclip, filename=None):
        """A function to calculate all offsets types for every fibre using data available from the database"""
        #Setting up the empty array and the ID value list
        self.id = ID
        #ID = np.arange(0, 1009).astype(list)
        #ID = list(ID)
        fill = np.empty((1009, 7))
        fill.fill(np.nan)
        fill[:,0] = ID
        #Grabbing all the offsets from the database entries
        off = offset_calc(ID)

        unpark = off.calculate_offset('unparks', plate=p, robot=r, sigmaclip=sigmaclip)#, iter=iter)
        unpark = np.asarray(unpark)

        park = off.calculate_offset('parks', plate=p, robot=r, sigmaclip=sigmaclip)#, iter=iter)
        park = np.asarray(park)

        move = off.calculate_offset('moves', plate=p, robot=r, sigmaclip=sigmaclip)#, iter=iter)
        move = np.asarray(move)

        #Iterating through each move offset calculated and entering into the empty array
        for index, item in enumerate(move):
            if int(item[0]) in ID:
                idx = int(item[0])
                move_x = item[1]
                move_y = item[2]
                fill[idx,1], fill[idx,2] = move_x, move_y
        for index, item in enumerate(unpark):
            if int(item[0]) in ID:
                idx = int(item[0])
                unpark_x = item[1]
                unpark_y = item[2]
                fill[idx,3], fill[idx,4] = unpark_x, unpark_y
        for index, item in enumerate(park):
            if int(item[0]) in ID:
                idx = int(item[0])
                park_x = item[1]
                park_y = item[2]
                fill[idx,5], fill[idx,6] = park_x, park_y
        df = pd.DataFrame(fill, columns=['ID', 'Move_X', 'Move_y', 'Unpark_x', 'Unpark_y', 'Park_x', 'Park_y'])
        self.df = df
        if type(filename)==str:
            #np.savetxt(filename, df.values, fmt='%f')
            self.df.to_csv(filename, index=False)
        return df


    
    def calculate_timings_indiv(self, fibid, move_type, p, r, show=True, dir='/home/slh/databse/'):
        assert move_type in moveslist, 'move_type must be either moves, unparks, or parks'
        assert type(fibid)==int, 'fibid must be an integer'
        dirname=dir+str(fibid)+'_'+move_type+'_timings.png'
        fd = fibre_database()
        e = fd.check_entries(fibid, move_type, plate=p, robot=r)
        timings = []
        for i in e:
            start = datetime.strptime(i[4], "%Y-%m-%d %H:%M:%S.%f")
            end = datetime.strptime(i[5], "%Y-%m-%d %H:%M:%S.%f")
            diff = (end - start).total_seconds()
            timings.append(diff)
        if show:
            timings = sorted(np.asarray(timings))
            plt.stem(timings)
            plt.xticks(np.arange(len(e)))
            plt.xlabel('Move number')
            plt.ylabel('Move time [s]')
            try:
                plt.show()
            except:
                plt.savefig('dirname')

        else:
            return sorted(np.asarray(timings))












