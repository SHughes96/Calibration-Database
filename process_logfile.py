import os
import sys
import re
import numpy as np
from create_database import fibre_database 
os.chdir(r'/home/pos_eng/WEAVE/fstest/')
from pos import *
import FSTest as fs
#os.chdir(r'/home/slh/database')
from astropy.stats import sigma_clip

class log_extraction():
    """A class to extract the fibre movement information from a logfile and store it in the database fibre_moves.db """
    
    def __init__(self, filename, plate='PLATE_A', robot=0, DIR='/home/pos_eng/WEAVE/'):
        self.logfile = filename
        self.plate = plate
        self.robot = robot
        self.dir = DIR
        self.moves_list = ['move', 'park', 'unpark']
        os.chdir(DIR)
        self.retry = False

        return
    
    def extract_fibres_moved(self, move_type, plate):
        """A function to generate a list of every fibre moved in the logfile """
        assert move_type in self.moves_list, 'Move type must be listed'
        if plate=='PLATE_A':
            _str = 'impl::'+move_type+'(0'
            _move_str = r"impl::"+move_type+"\(0,(.*?)(?=,)"
        else:
            _str = 'impl::'+move_type+'(1'
            _move_str = r"impl::"+move_type+"\(1,(.*?)(?=,)"


        f = open(self.logfile)
        ch = f.read()
        self.ch = ch
        f.close()
        fibs_set = list(set(np.asarray(re.findall(_move_str, ch)).astype(int)))


        self.move = False
        self.unpark = False
        self.park = False

        if move_type=='unpark':
            self.unpark = True
        elif move_type=='move':
            self.move = True
        else:
            self.park = True
 
        return fibs_set
    

    def find_move_info(self, fibre_id, move_type):
        assert move_type in self.moves_list, 'Move type must be listed'
        if self.plate=='PLATE_A':
            a = fs.OneMove(int(fibre_id), POSLIB.PLATE_A)
            p = 0
        else:
            a = fs.OneMove(int(fibre_id), POSLIB.PLATE_B)
            p = 1

        if move_type=='unpark':
            self.unpark = True
        elif move_type=='move':
            self.move = True
        else:
            self.park = True

        self.traj = np.asarray(a.find_trajectory(p,self.robot,self.move,self.park,self.unpark, logfile=a.lastlog(str(self.logfile)))).transpose()
        self.carry=np.asarray(a.find_elements(p,self.robot,self.move,self.park,self.unpark, 'expected offset (pixels):',logfile=a.lastlog(str(self.logfile)))).transpose()[3:][::2]
        self.gripper=np.asarray(a.find_elements(p,self.robot,self.move,self.park,self.unpark, 'position (gripper coords):', logfile=a.lastlog(str(self.logfile)))).transpose()[3:][::2]
        self.release=np.asarray(a.find_elements(p,self.robot,self.move,self.park,self.unpark, 'release offset:', logfile=a.lastlog(str(self.logfile)))).transpose()


        return self.traj, self.carry, self.gripper, self.release

    def updated_find_timestamps_and_positions(self, fibre_id, movetype, new_p=None):
        assert movetype in self.moves_list, 'Move type must be of one listed'
        
        p = 0
        pl = POSLIB.PLATE_A
        if self.plate=='PLATE_B':
            p = 1
            pl = POSLIBl.PLATE_B
        if new_p is not None:
            print('Updating plate value')
            p = new_p
            if p==0:
                pl = POSLIB.PLATE_A
            else:
                pl = POSLIB.PLATE_B
        a = fs.OneMove(int(fibre_id), pl)

        a.robot = self.robot ###this may cause issues

        self.traj = []
        self.release = []
        self.exp_offset = []
        self.pos_gripper = []
        self.move_start = []
        self.move_end = []
        self.targ_xy = []

        self.retry_traj = []
        self.retry_release = []
        self.retry_exp_offset = []
        self.retry_pos_gripper = []
        self.retry_move_start = []
        self.retry_move_end = []
        self.retry_targ_xy = []


        self.retry = False
        if movetype=='unpark':
            #self.retry = False
            self.unparks = True
            #retry stuff was here

            bits = a.find_last_moves(p, a.fibid, self.dir+self.logfile, False, False, True)
            print('Length of bits.........', len(bits))
            moves_back = len(bits)#200
            ########temporarily removing this so that it loops through every iteration returned
            #if len(bits)<200:
                #moves_back = len(bits)
            self.iterate = []
            self.iterate_ids = []
            #el = 36
            #if a.tier==1.0:
                #el +=1
            for i in range(-1, -moves_back-1, -1):
                self.retry = False
                print(i)
                el = 36
                lines = bits[i].split('INFO Fibre')[0].split('\n')
                for index,item in enumerate(lines):
                    if 'retrying' in item:
                        self.retry = True

                self.cut = False
                #ERROR Could not locate fibre
                try:
                    error_case = [index for index,item in enumerate(lines) if 'ERROR' in item]
                    if len(error_case)!=0:
                        print('Could not locate fibre'+str(a.fibid)+'......skipping')
                        continue
                    test_case = [index for index,item in enumerate(lines) if '::unpark(' in item][0]
                    print('Starting index ', test_case)
                    self.lines = lines
                except:
                    print('No unparks found for fibre'+str(a.fibid)+'......skipping')
                    continue
                if len(lines)>43:
                    print('reducing lines')
                    if '::unpark(' not in lines[1]:
                        idx = [index for index, item in enumerate(lines) if '::unpark(' in item]
                        if len(idx)==2:
                            idx = idx[1]
                            self.cut = True
                        else:
                            idx = idx[0]
                        lines = lines[idx-1:idx+68]
                        self.lines = lines
                    else:
                        lines = lines[0:68]
                        self.lines = lines

                ##putting in shift conditions here
                if a.tier==1.0 and 'current button' not in self.lines[5]:
                    el+=1
                    idx_rel = 21
                elif a.tier!=1.0 and 'current button' not in self.lines[5]:
                    idx_rel = 21
                elif a.tier!=1.0 and 'current button' in self.lines[5]:
                    el = 35
                    idx_rel = 20
                elif a.tier==1.0 and self.cut and 'current button' in self.lines[5]:
                    el = 35
                    idx_rel = 20
                else:
                    idx_rel = 20

                ##putting in backup plan for some cases:
                if 'DEBUG fibre position (pixel coords):' in self.lines[el]:
                    el+=1
                elif 'DEBUG expected offset (pixels):' in self.lines[el]:
                    el-=1
                elif 'DEBUG move_one_fibre::get_fibre_position()' in self.lines[el]:
                    el+=2
                
                if 'DEBUG release offset:' not in self.lines[idx_rel]:
                    for kindex, kitem in enumerate(self.lines):
                        if 'DEBUG release offset:' in kitem:
                            idx_rel = kindex
                            break

                start_time = ' '.join(lines[1][1:27].split('T')) 
                end_time = ' '.join(lines[el+4][1:27].split('T'))  
                #eo = lines[el+1].split(':')[-1].split(',')
                pos = lines[el].split(':')[-1].split(',')
                idx_end = el +4
                self.el = el
                if 'retrying' in self.lines[idx_end] or 'fibre position error' not in self.lines[idx_end]:
                    idx_end -=1
                    self.idx_end = idx_end 
                    self.idx_rel = idx_rel
                    self.el = el
                pe = lines[idx_end].split(':')[-1].split(',')
                rel = lines[idx_rel].split(':')[-1].split(',') #lines[el-16].split(':')[-1].split(',')
                eo = lines[idx_rel-1].split(':')[-1].split(',')
                targ = lines[idx_end-1].split(':')[-1].split(',')

                self.pe = pe
                self.eo = eo
                self.pos = pos
                self.rel = rel
                self.targ= targ

                self.traj.append((float(pe[-2]),  float(pe[-1])))
                self.exp_offset.append((float(eo[-2]), float(eo[-1]) ))
                self.pos_gripper.append((float(pos[-2]), float(pos[-1])))
                self.release.append((float(rel[-2]), float(rel[-1])))

                self.move_start.append(start_time)
                self.move_end.append(end_time)
                self.targ_xy.append((float(targ[-2]), float(targ[-1])))

                if self.retry:
                    try:
                        self.iterate.append(i)
                        self.iterate_ids.append(a.fibid)
                    
                        r_pos = lines[el+26].split(':')[-1].split(',') 
                        r_pe = lines[el+30].split(':')[-1].split(',')  
                        r_rel = lines[el+15].split(':')[-1].split(',') 
                        r_eo = lines[el+14].split(':')[-1].split(',')
                        r_start = ' '.join(lines[el+5][1:27].split('T')) 
                        r_end = ' '.join(lines[el+30][1:27].split('T')) 

                        self.retry_traj.append((float(r_pe[-2]),  float(r_pe[-1])))
                        self.retry_exp_offset.append((float(r_eo[-2]), float(r_eo[-1]) ))
                        self.retry_pos_gripper.append((float(r_pos[-2]), float(r_pos[-1])))
                        self.retry_release.append((float(r_rel[-2]), float(r_rel[-1])))
                        self.retry_move_start.append(r_start)
                        self.retry_move_end.append(r_end)
                        self.retry_targ_xy.append((float(targ[-2]), float(targ[-1])))
                                    
        
                    except:
                        print('Move iteration failed to be processed')
                        self.retry = False
            
            self.traj = np.asarray(self.traj)
            self.release = np.asarray(self.release)
            self.exp_offset = np.asarray(self.exp_offset)
            self.pos_gripper = np.asarray(self.pos_gripper)
            self.move_start = np.asarray(self.move_start)
            self.move_end = np.asarray(self.move_end)
            self.targ_xy = np.asarray(self.targ_xy)

            #if self.retry:
            #print('Return with retry')
            self.retry_traj = np.asarray(self.retry_traj)
            self.retry_release = np.asarray(self.retry_release) 
            self.retry_exp_offset = np.asarray(self.retry_exp_offset)
            self.retry_pos_gripper = np.asarray(self.retry_pos_gripper)
            self.retry_move_start = np.asarray(self.retry_move_start)
            self.retry_move_end = np.asarray(self.retry_move_end)
            self.retry_targ_xy = np.asarray(self.retry_targ_xy)

            return self.traj, self.release, self.exp_offset, self.pos_gripper, self.move_start, self.move_end, self.targ_xy, self.retry_traj, self.retry_release, self.retry_exp_offset, self.retry_pos_gripper, self.retry_move_start, self.retry_move_end, self.retry_targ_xy


            #return self.traj, self.release, self.exp_offset, self.pos_gripper, self.move_start, self.move_end, self.targ_xy


        elif movetype=='park':
            self.retry = False
            self.parks = True
            bits = a.find_last_moves(p, a.fibid, self.dir+self.logfile, False, True, False)
            moves_back = len(bits)#200
            #if len(bits)<200:
                #moves_back = len(bits)
            print('moves back', moves_back)
            #if a.tier==1.0:
                #el+=1
            for i in range(-1, -moves_back-1, -1):
                el=37
                lines = bits[i].split('INFO Fibre')[0].split('\n')
                for index,item in enumerate(lines):
                    if 'retrying' in item:
                        self.retry = True
                try:
                    error_case = [index for index,item in enumerate(lines) if 'ERROR' in item]
                    if len(error_case)!=0:
                        print('Could not locate fibre......skipping')
                        continue
                    test_case = [index for index,item in enumerate(lines) if '::park(' in item][0]
                    #print('Starting index.....', test_case)
                    self.lines = lines
                except:
                    print('No parks found....skipping')
                    continue

                self.lines = lines
                if len(lines)>43:
                    if '::park(' not in lines[1]:
                        idx = [index for index, item in enumerate(lines) if '::park(' in item]
                        if len(idx)==2:
                            idx = idx[1]
                        else:
                            idx = idx[0]
                        lines = lines[idx-1:idx+43]
                        #print('Park lines reduced', idx)
                        self.lines = lines
                    else:
                        lines = lines[0:43]
                        self.lines = lines

                if a.tier==1.0 and 'current button' not in self.lines[5]:
                    idx_rel = 21
                    el +=1
                elif a.tier!=1.0 and 'current button' not in self.lines[5]:
                    idx_rel = 21
                else:
                    idx_rel = 20

                ##putting in backup plan for some cases:
                if 'DEBUG fibre position (pixel coords):' in self.lines[el]:
                    el+=1
                elif 'DEBUG expected offset (pixels):' in self.lines[el]:
                    el-=1
                elif 'DEBUG move_one_fibre::get_fibre_position()' in self.lines[el]:
                    el+=2
                
                if 'DEBUG release offset:' not in self.lines[idx_rel]:
                    for kindex, kitem in enumerate(self.lines):
                        if 'DEBUG release offset:' in kitem:
                            idx_rel = kindex
                            break
                start_time = ' '.join(lines[1][1:27].split('T'))
                end_time = ' '.join(lines[el+4][1:27].split('T'))
                #eo = lines[el+1].split(':')[-1].split(',')
                pos = lines[el].split(':')[-1].split(',')
                idx_end = el+4
                self.el = el
                if 'retrying' in self.lines[idx_end] or 'fibre position error' not in self.lines[idx_end]:
                    idx_end -=1
                pe = lines[idx_end].split(':')[-1].split(',')
                rel = lines[idx_rel].split(':')[-1].split(',')#lines[el-18].split(':')[-1].split(',')
                eo = lines[idx_rel-1].split(':')[-1].split(',')
                targ = lines[idx_end-1].split(':')[-1].split(',')

                self.rel = rel
                self.pos = pos
                self.eo =eo
                self.pe = pe
                self.targ = targ

                self.traj.append((float(pe[-2]),  float(pe[-1])))
                self.exp_offset.append((float(eo[-2]), float(eo[-1]) ))
                self.pos_gripper.append((float(pos[-2]), float(pos[-1])))
                self.release.append((float(rel[-2]), float(rel[-1])))

                self.move_start.append(start_time)
                self.move_end.append(end_time)
                self.targ_xy.append((float(targ[-2]), float(targ[-1])))

                if self.retry:
                    try:
                        self.iterate.append(i)
                        self.iterate_ids.append(a.fibid)
                    
                        r_pos = lines[el+26].split(':')[-1].split(',') 
                        r_pe = lines[el+30].split(':')[-1].split(',')  
                        r_rel = lines[el+15].split(':')[-1].split(',') 
                        r_eo = lines[el+14].split(':')[-1].split(',')
                        r_start = ' '.join(lines[el+5][1:27].split('T')) 
                        r_end = ' '.join(lines[el+30][1:27].split('T')) 

                        self.retry_traj.append((float(r_pe[-2]),  float(r_pe[-1])))
                        self.retry_exp_offset.append((float(r_eo[-2]), float(r_eo[-1]) ))
                        self.retry_pos_gripper.append((float(r_pos[-2]), float(r_pos[-1])))
                        self.retry_release.append((float(r_rel[-2]), float(r_rel[-1])))
                        self.retry_move_start.append(r_start)
                        self.retry_move_end.append(r_end)
                        self.retry_targ_xy.append((float(targ[-2]), float(targ[-1])))
                                    
        
                    except:
                        print('Move iteration failed to be processed')
                        self.retry = False


            self.traj = np.asarray(self.traj)
            self.release = np.asarray(self.release)
            self.exp_offset = np.asarray(self.exp_offset)
            self.pos_gripper = np.asarray(self.pos_gripper)
            self.move_start = np.asarray(self.move_start)
            self.move_end = np.asarray(self.move_end)
            self.targ_xy = np.asarray(self.targ_xy)

            self.retry_traj = np.asarray(self.retry_traj)
            self.retry_release = np.asarray(self.retry_release) 
            self.retry_exp_offset = np.asarray(self.retry_exp_offset)
            self.retry_pos_gripper = np.asarray(self.retry_pos_gripper)
            self.retry_move_start = np.asarray(self.retry_move_start)
            self.retry_move_end = np.asarray(self.retry_move_end)
            self.retry_targ_xy = np.asarray(self.retry_targ_xy)

            return self.traj, self.release, self.exp_offset, self.pos_gripper, self.move_start, self.move_end, self.targ_xy, self.retry_traj, self.retry_release, self.retry_exp_offset, self.retry_pos_gripper, self.retry_move_start, self.retry_move_end, self.retry_targ_xy



            #return self.traj, self.release, self.exp_offset, self.pos_gripper, self.move_start, self.move_end, self.targ_xy 

        else:
            self.moves = True
            self.retry = False
            bits = a.find_last_moves(p, a.fibid, self.dir+self.logfile, True, False, False)
            print('Bits length is....', len(bits))
            moves_back = len(bits)#200
            #if len(bits)<200:
                #moves_back = len(bits)
            #el = 36
            #if a.tier==1.0:
             #   el+=1
            for i in range(-1, -moves_back-1, -1):
                el = 37
                lines = bits[i].split('INFO Fibre')[0].split('\n')
                for index,item in enumerate(lines):
                    if 'retrying' in item:
                        self.retry = True
                print(i)
                try:
                    error_case = [index for index,item in enumerate(lines) if 'ERROR' in item]
                    if len(error_case)!=0:
                        print('Could not locate fibre......skipping')
                        continue
                    test_case = [index for index, item in enumerate(lines) if '::move(' in item][0]
                    #print('starting index ',test_case)
                    self.lines = lines
                except:
                    print('No moves found in this group... skipping')
                    continue
                if len(lines)>43:
                    print('reducing lines')
                    if '::move(' not in lines[1]:
                        idx = [index for index, item in enumerate(lines) if '::move(' in item]
                        if len(idx)==2:
                            idx = idx[1]
                        else:
                            idx = idx[0]
                        lines = lines[idx-1:idx+43]
                        self.lines = lines
                    else:
                        lines = lines[0:43]
                        self.lines = lines
                ## shifting conditions
                if a.tier==1.0 and 'current button' not in self.lines[5]:
                    #el+=1
                    idx_rel = 21
                elif a.tier!=1.0 and 'current button' not in self.lines[5]:
                    idx_rel = 21
                else:
                    idx_rel = 20

                ##putting in backup plan for some cases:
                if 'DEBUG fibre position (pixel coords):' in self.lines[el]:
                    el+=1
                elif 'DEBUG expected offset (pixels):' in self.lines[el]:
                    el-=1
                elif 'DEBUG move_one_fibre::get_fibre_position()' in self.lines[el]:
                    el+=2

                if 'DEBUG release offset:' not in self.lines[idx_rel]:
                    for kindex, kitem in enumerate(self.lines):
                        if 'DEBUG release offset:' in kitem:
                            idx_rel = kindex
                            break
                start_time = ' '.join(lines[1][1:27].split('T'))
                end_time = ' '.join(lines[el+4][1:27].split('T'))
                
                pos = lines[el].split(':')[-1].split(',')
                idx_end = el + 4
                self.el = el
                if 'retrying' in self.lines[idx_end] or 'fibre position error' not in self.lines[idx_end]:
                    idx_end -=1
                    print('End idx changes to ', idx_end)
                pe = lines[idx_end].split(':')[-1].split(',')
                rel = lines[idx_rel].split(':')[-1].split(',')
                eo = lines[idx_rel-1].split(':')[-1].split(',') #lines[el+1].split(':')[-1].split(',')
                targ = lines[idx_end-1].split(':')[-1].split(',')
                
                self.rel = rel
                self.pe = pe
                self.pos = pos
                self.eo = eo
                self.targ = targ

                self.traj.append((float(pe[-2]), float(pe[-1])))
                self.release.append((float(rel[-2]), float(rel[-1])))
                self.exp_offset.append((float(eo[-2]), float(eo[-1])))
                self.pos_gripper.append((float(pos[-2]), float(pos[-1])))
                self.targ_xy.append((float(targ[-2]), float(targ[-1])))

                self.move_start.append(start_time)
                self.move_end.append(end_time)

                if self.retry:
                    try:
                        self.iterate.append(i)
                        self.iterate_ids.append(a.fibid)
                    
                        r_pos = lines[el+26].split(':')[-1].split(',') 
                        r_pe = lines[el+30].split(':')[-1].split(',')  
                        r_rel = lines[el+15].split(':')[-1].split(',') 
                        r_eo = lines[el+14].split(':')[-1].split(',')
                        r_start = ' '.join(lines[el+5][1:27].split('T')) 
                        r_end = ' '.join(lines[el+30][1:27].split('T')) 

                        self.retry_traj.append((float(r_pe[-2]),  float(r_pe[-1])))
                        self.retry_exp_offset.append((float(r_eo[-2]), float(r_eo[-1]) ))
                        self.retry_pos_gripper.append((float(r_pos[-2]), float(r_pos[-1])))
                        self.retry_release.append((float(r_rel[-2]), float(r_rel[-1])))
                        self.retry_move_start.append(r_start)
                        self.retry_move_end.append(r_end)
                        self.retry_targ_xy.append((float(targ[-2]), float(targ[-1])))
                                    
        
                    except:
                        print('Move iteration failed to be processed')
                        self.retry = False


            self.traj = np.asarray(self.traj)
            self.release = np.asarray(self.release)
            self.exp_offset = np.asarray(self.exp_offset)
            self.pos_gripper = np.asarray(self.pos_gripper)
            self.move_start = np.asarray(self.move_start)
            self.move_end = np.asarray(self.move_end)
            self.targ_xy = np.asarray(self.targ_xy)

            self.retry_traj = np.asarray(self.retry_traj)
            self.retry_release = np.asarray(self.retry_release) 
            self.retry_exp_offset = np.asarray(self.retry_exp_offset)
            self.retry_pos_gripper = np.asarray(self.retry_pos_gripper)
            self.retry_move_start = np.asarray(self.retry_move_start)
            self.retry_move_end = np.asarray(self.retry_move_end)
            self.retry_targ_xy = np.asarray(self.retry_targ_xy)

            return self.traj, self.release, self.exp_offset, self.pos_gripper, self.move_start, self.move_end, self.targ_xy, self.retry_traj, self.retry_release, self.retry_exp_offset, self.retry_pos_gripper, self.retry_move_start, self.retry_move_end, self.retry_targ_xy


            #return self.traj, self.release, self.exp_offset, self.pos_gripper, self.move_start, self.move_end, self.targ_xy

        return


    def find_timestamps_and_positions(self, fibre_id, movetype):
        assert movetype in self.moves_list, 'move type must be of one listed'
        p = 0
        a = fs.OneMove(int(fibre_id), POSLIB.PLATE_A)
        if self.plate=='PLATE_B':
            p = 1
            a = fs.OneMove(int(fibre_id), POSLIB.PLATE_B)

        bits = a.find_last_moves(p, a.fibid, self.dir+self.logfile, self.move, self.park, self.unpark)
        last = bits[-1].split('\n')

        first_index = []
        last_index = []
        move_start_index = []

        for index, item in enumerate(last):
            if '::'+str(movetype)+'('+str(p)+','+str(fibre_id) in item:
                first_index.append(index)
        for i in range(first_index[0], len(last)):
            if 'placed at' in last[i]:
                last_index.append(i)
                break
        for i in range(first_index[0], len(last)):
            if 'INFO open gripper' in last[i]:
                move_start_index.append(i)
                break

        self.move_start_time = ' '.join(last[move_start_index[0]][1:27].split('T'))
        self.move_end_time = ' '.join(last[last_index[0]][1:27].split('T'))

        self.targx = float(last[first_index[0]].split(',')[-1][:-1])
        self.targy = float(last[first_index[0]].split(',')[-2])
        return self.move_start_time, self.move_end_time, self.targx, self.targy



class database_entry(log_extraction):
    ##List of entry inputs
    '''Fibreid INTEGER,
    Robot INTEGER,
    Plate INTEGER,
    Move_start DATETIME PRIMARY KEY,
    Move_end DATETIME,
    Traj_X REAL,
    Traj_Y REAL,
    Release_X REAL,
    Release_Y REAL,
    Carry_X REAL,
    Carry_Y REAL,
    Gripper_X REAL,
    Gripper_Y REAL,
    Targ_X REAL,
    Targ_Y REAL,
    Rot NULL,
    Elev NULL '''

    ##Note: the timestamp refers only to the move start and to the placement end, it does not time the iterations (this could possibly be changed with more work)


    def __init__(self, filename, plate, robot, DIR, Rot='NULL', Elev='NULL', backup=False):
        self.cap = 500
        assert positioner.getState().online, 'Positioner must be online to process logfiles'
        assert plate=='PLATE_A' or plate=='PLATE_B', 'Set plate to either PLATE_A or PLATE_B'
        assert robot==0 or robot==1, 'Set robot as 0 or 1 for Morta and Nona respectively'
        assert type(filename)==str and type(DIR)==str, 'Filenames and directory must be entered as a string'
        assert type(Elev)==str and type(Rot)==str, 'Elevation and rotation must be entered as a string'
        self.plate_list = [0, 1]
        os.chdir('/home/pos_eng/WEAVE/pos/positioner/python/FIBRE_CALIB_STORE/database/')
        self.logfile = filename
        self.prev_files = np.loadtxt('files_in_database.txt', dtype=str)
        #try:
        self.log_idx = [index for index,item in enumerate(self.prev_files[:,0]) if filename in item]
        print(self.log_idx)
        for i in self.log_idx:
            assert filename not in self.prev_files[:,0] and plate[-1]!=self.prev_files[int(i),1], 'Logfile has already been processed for '+plate
        #except:
            #print('Logfile has not been processed before')
        #if filename not in self.prev_files[:,0]:
        #with open('files_in_database.txt', "a") as self.f:
        self.f = open('files_in_database.txt', "a") #.write(filename+", "+plate[-1]+"\n")
            #f.write("\n")
            #f.close()
        print('Logfile added to processing list')
        self.fd = fibre_database(backup=backup)
        self.columns = ['Move_id', 'Fibreid', 'Robot', 'Plate', 'Move_start', 'Move_end', 'Traj_X', 'Traj_Y', 'Release_X', 'Release_Y', 'Carry_X', 'Carry_Y', 'Gripper_X', 'Gripper_Y', 'Targ_X', 'Targ_Y', 'Rot', 'Elev']
        try:
            self.fd.create_tables()
        except:
            print('Tables already exist')

        super().__init__(filename, plate, robot, DIR)
        self.rot = Rot
        self.elev = Elev
        self.filename = filename
        ##extracting the relevent move types
        self._parks = super().extract_fibres_moved('park', plate)
        self._unparks = super().extract_fibres_moved('unpark', plate)
        self._moves = super().extract_fibres_moved('move', plate)
        self.p = 0
        if plate=='PLATE_B':
            self.p = 1
        return

    def add_fibre_move_entries(self, new_p=None):#plate=self.p):
        #testing this for just moves
        if new_p is not None:
            self.p = new_p
        self.flagged = []
        self.track_entries = []
        for index, item in enumerate(self._moves):
            self.item = item #take this out once no longer needed
            try:
                #t,c,g,r = super().find_move_info(item, 'move')
                output = super().updated_find_timestamps_and_positions(item, 'move', new_p=new_p)
                t,r,c,g, ms, me, targ = output[:7] #super().updated_find_timestamps_and_positions(item, 'move', new_p=new_p)
                if len(t)==0:
                    continue
                if len(t)!=len(g):
                    continue
                t,r,c,g,ms,me,targ = t[:self.cap], r[:self.cap], c[:self.cap], g[:self.cap], ms[:self.cap], me[:self.cap], targ[:self.cap]
                if self.retry:
                    t,r,c,g, ms, me, targ, re_t, re_r, re_c, re_g, re_ms, re_me, re_targ = output[:14]
                    t,r,c,g,ms,me,targ, re_t, re_r, re_c, re_g, re_ms, re_me, re_targ = t[:self.cap], r[:self.cap], c[:self.cap], g[:self.cap], ms[:self.cap], me[:self.cap], targ[:self.cap], re_t[:self.cap], re_r[:self.cap], re_c[:self.cap], re_g[:self.cap], re_ms[:self.cap], re_me[:self.cap], re_targ[:self.cap]
            #try:
                #timepos = super().find_timestamps_and_positions(item, 'move')
            except Exception as e:
                print(item, e)
                self.flagged.append((self.item, 'move'))
                exception_type, exception_object, exception_traceback = sys.exc_info()
                filename = exception_traceback.tb_frame.f_code.co_filename
                line_number = exception_traceback.tb_lineno

                print("Exception type: ", exception_type)
                print("File name: ", filename)
                print("Line number: ", line_number)
                #print('Function output', super().updated_find_timestamps_and_positions(item, 'move', new_p=new_p))
                continue
            except IndexError as te:
                # print(item, e)
                # self.flagged.append((self.item, 'move'))
                # exception_type, exception_object, exception_traceback = sys.exc_info()
                # filename = exception_traceback.tb_frame.f_code.co_filename
                # line_number = exception_traceback.tb_lineno

                # print("Exception type: ", exception_type)
                # print("File name: ", filename)
                # print("Line number: ", line_number)
                print('Function output', super().updated_find_timestamps_and_positions(item, 'move', new_p=new_p))
                continue
            #try:
            for jindex, jitem in enumerate(t):
                    try:
                    #need to check this is working correctly
                        entry = (int(item), self.robot, self.p, ms[jindex], me[jindex], t[jindex][0], t[jindex][1], r[jindex][0], r[jindex][1], c[jindex][0], c[jindex][1], g[jindex][0], g[jindex][1], targ[jindex][0], targ[jindex][1], self.rot, self.elev, self.logfile)
                        self.track_entries.append([item, 'move', self.p])
                        if self.fd.check_count(item, 'moves')[0][0]<self.cap:
                            self.fd.add_move(entry, tble='moves')
                        else:
                            self.fd.update_move(entry, 'moves', item)

                    except Exception as e:
                        print(item, e)
                        self.flagged.append((self.item, 'move'))
                        exception_type, exception_object, exception_traceback = sys.exc_info()
                        filename = exception_traceback.tb_frame.f_code.co_filename
                        line_number = exception_traceback.tb_lineno

                        print("Exception type: ", exception_type)
                        print("File name: ", filename)
                        print("Line number: ", line_number)
                        print('Function output', entry) 
                              #super().updated_find_timestamps_and_positions(item, 'move', new_p=new_p))
                        continue

            

        for index, item in enumerate(self._parks):
            self.item = item
            try:
                #t,c,g,r = super().find_move_info(item, 'park')
                output = super().updated_find_timestamps_and_positions(item, 'park', new_p=new_p)
                t,r,c,g, ms, me, targ = output[:7]#super().updated_find_timestamps_and_positions(item, 'park', new_p=new_p)
                if len(t)==0:
                    continue
                if len(t)!=len(g):
                    continue
                #t,g,c,r = t[-20:], g[-20:], c[-20:], r[-20:]
                t,r,c,g,ms,me,targ = t[:self.cap], r[:self.cap], c[:self.cap], g[:self.cap], ms[:self.cap], me[:self.cap], targ[:self.cap]

                if self.retry:
                    t,r,c,g, ms, me, targ, re_t, re_r, re_c, re_g, re_ms, re_me, re_targ = output[:14]
                    t,r,c,g,ms,me,targ, re_t, re_r, re_c, re_g, re_ms, re_me, re_targ = t[:self.cap], r[:self.cap], c[:self.cap], g[:self.cap], ms[:self.cap], me[:self.cap], targ[:self.cap], re_t[:self.cap], re_r[:self.cap], re_c[:self.cap], re_g[:self.cap], re_ms[:self.cap], re_me[:self.cap], re_targ[:self.cap]
            #try:
                #timepos = super().find_timestamps_and_positions(item, 'park')
            except Exception as e:
                print(item, e)
                self.flagged.append((self.item, 'park'))
                exception_type, exception_object, exception_traceback = sys.exc_info()
                filename = exception_traceback.tb_frame.f_code.co_filename
                line_number = exception_traceback.tb_lineno

                print("Exception type: ", exception_type)
                print("File name: ", filename)
                print("Line number: ", line_number)
                #print('Function output', super().updated_find_timestamps_and_positions(item, 'park', new_p=new_p))
                continue
                    

            #try:
            for jindex, jitem in enumerate(t):
                    try:
                        entry = (int(item), self.robot, self.p, ms[jindex], me[jindex],t[jindex][0], t[jindex][1], r[jindex][0], r[jindex][1], c[jindex][0], c[jindex][1], g[jindex][0], g[jindex][1], targ[jindex][0], targ[jindex][1], self.rot, self.elev, self.logfile)
                        self.track_entries.append([item, 'park', self.p])
                        if self.fd.check_count(item, 'parks')[0][0]<self.cap:
                            self.fd.add_move(entry, tble='parks')
                            print('Entry added')
                        else:
                            self.fd.update_move(entry, 'parks', item)
                            print('Entry added')
                    except Exception as e:
                        print(item, e)
                        self.flagged.append((self.item, 'park'))
                        exception_type, exception_object, exception_traceback = sys.exc_info()
                        filename = exception_traceback.tb_frame.f_code.co_filename
                        line_number = exception_traceback.tb_lineno

                        print("Exception type: ", exception_type)
                        print("File name: ", filename)
                        print("Line number: ", line_number)
                        print('Function output', entry) 
                        #super().updated_find_timestamps_and_positions(item, 'park', new_p=new_p))
                        continue


        for index, item in enumerate(self._unparks):
            self.item = item

            try:
                output = super().updated_find_timestamps_and_positions(item, 'unpark', new_p=new_p)
                t,r,c,g, ms, me, targ = output[:7]
                if len(t)==0:
                    continue
                if len(t)!=len(g):
                    continue
                #t,g,c,r = t[-20:], g[-20:], c[-20:], r[-20:]
                t,r,c,g,ms,me,targ = t[:self.cap], r[:self.cap], c[:self.cap], g[:self.cap], ms[:self.cap], me[:self.cap], targ[:self.cap]

                re_t = output[8]
                if len(re_t)!=0: 
                #if self.retry:
                    t,r,c,g, ms, me, targ, re_t, re_r, re_c, re_g, re_ms, re_me, re_targ = output[:14]
                    t,r,c,g,ms,me,targ, re_t, re_r, re_c, re_g, re_ms, re_me, re_targ = t[:self.cap], r[:self.cap], c[:self.cap], g[:self.cap], ms[:self.cap], me[:self.cap], targ[:self.cap], re_t[:self.cap], re_r[:self.cap], re_c[:self.cap], re_g[:self.cap], re_ms[:self.cap], re_me[:self.cap], re_targ[:self.cap]
            
            except Exception as e:
                #
                self.flagged.append((self.item, 'unpark'))
                print('Exception caught', item, e)
                exception_type, exception_object, exception_traceback = sys.exc_info()
                filename = exception_traceback.tb_frame.f_code.co_filename
                line_number = exception_traceback.tb_lineno

                print("Exception type: ", exception_type)
                print("File name: ", filename)
                print("Line number: ", line_number)
                #print('Function output', super().updated_find_timestamps_and_positions(item, 'unpark',new_p=new_p))
                continue

            ##### putting in the entires added here instead
            #try:
            for jindex, jitem in enumerate(t):
                #
                try:    
                    entry = (int(item), self.robot, self.p, ms[jindex], me[jindex],t[jindex][0], t[jindex][1], r[jindex][0], r[jindex][1], c[jindex][0], c[jindex][1], g[jindex][0], g[jindex][1], targ[jindex][0], targ[jindex][1], self.rot, self.elev, self.logfile)
                    self.track_entries.append([item, 'unpark', self.p])
                    if self.fd.check_count(item, 'unparks')[0][0]<self.cap:
                        self.fd.add_move(entry, tble='unparks')
                        print('Entry added')
                    else:
                        self.fd.update_move(entry, 'unparks', item)
                        print('Entry added')
                except Exception as e:
                    #
                    self.flagged.append((self.item, 'unpark'))
                    print('Exception caught', item, e)
                    exception_type, exception_object, exception_traceback = sys.exc_info()
                    filename = exception_traceback.tb_frame.f_code.co_filename
                    line_number = exception_traceback.tb_lineno

                    print("Exception type: ", exception_type)
                    print("File name: ", filename)
                    print("Line number: ", line_number)
                    print('Function output', entry)
                    #print('Function output', super().updated_find_timestamps_and_positions(item, 'unpark', new_p=new_p))
                    continue
            
            #if self.retry:
            if len(re_t)!=0:
                #try:
                for jindex, jitem in enumerate(re_t):
                        try:
                            entry_iterate = (int(item), self.robot, self.p, re_ms[jindex], re_me[jindex], re_t[jindex][0], re_t[jindex][1], re_r[jindex][0], re_r[jindex][1], re_c[jindex][0], re_c[jindex][1], re_g[jindex][0], re_g[jindex][1], re_targ[jindex][0], re_targ[jindex][1], self.rot, self.elev, self.logfile)
                            self.entry_iterate = entry_iterate
                            self.track_entries.append([item, 'move iteration', self.p])
                            if self.fd.check_count(item, 'moves')[0][0]<self.cap:
                                self.fd.add_move(entry_iterate, tble='moves')
                            else:
                                self.fd.update_move(entry_iterate, 'moves', item)
                        except Exception as e:
                            self.flagged.append((self.item, 'move iteration'))
                            print('Exception caught', item, e)
                            exception_type, exception_object, exception_traceback = sys.exc_info()
                            filename = exception_traceback.tb_frame.f_code.co_filename
                            line_number = exception_traceback.tb_lineno

                            print("Exception type: ", exception_type)
                            print("File name: ", filename)
                            print("Line number: ", line_number)
                            print('Function Ouput', entry)
                            #print('Function output', super().updated_find_timestamps_and_positions(item, 'unpark', new_p=new_p))
                            continue
            


        return 'Entries added'

    def evaluate_logfile(self):
        self.track_entries = np.asarray(self.track_entries, dtype='object')
        if self.track_entries.size==0:
            return 'No entries were processed in this log for this plate'
        types = ['park', 'unpark', 'move', 'move iteration']
        all_entries = list(set(self.track_entries[:,0]))
        for i in all_entries:
            info = []
            for j in types:
                N = len([item[1] for index, item in enumerate(self.track_entries) if item[0]==i and item[1]==j])
                info.append(f'{N} {j} entries ')
            print(f'Fibre {i} had {info[0]} {info[1]} {info[2]} {info[3]} added for PLATE_A')

        return


    def add_entries_both_plates(self):
        for i in self.log_idx:
            assert self.filename not in self.prev_files[:,0] and plate[-1]!=self.prev_files[int(i),1], 'Logfile has already been processed for '+plate
        print('Processing PLATE_A')
        new_p = 0
        plate = 'PLATE_A'
        print('Plate A ', new_p)
        self._parks = super().extract_fibres_moved('park', plate='PLATE_A')
        self._unparks = super().extract_fibres_moved('unpark', plate='PLATE_A')
        self._moves = super().extract_fibres_moved('move', plate='PLATE_A')
        print('Parks PLATE_A', self._parks)
        print('Unparks PLATE_A', self._unparks)
        print('Moves PLATE_A', self._moves)
        self.add_fibre_move_entries(new_p=new_p)
        print('PLATE_A flagged entries', self.flagged)
        #with open('files_in_database.txt', "a") as f:
        self.f.write(self.logfile+", "+plate[-1]+"\n")
            #f.close()
        self.evaluate_logfile()
        print('Processing PLATE_B')
        new_p = 1
        plate = 'PLATE_B'
        for i in self.log_idx:
            assert self.filename not in self.prev_files[:,0] and plate[-1]!=self.prev_files[int(i),1], 'Logfile has already been processed for '+plate
        print('PLATE B ', new_p)
        self._parks = super().extract_fibres_moved('park', plate='PLATE_B')
        self._unparks = super().extract_fibres_moved('unpark', plate='PLATE_B')
        self._moves = super().extract_fibres_moved('move', plate='PLATE_B')
        print('Parks PLATE_B', self._parks)
        print('Unparks PLATE_B', self._unparks)
        print('Moves PLATE_B', self._moves)
        self.add_fibre_move_entries(new_p=new_p)
        self.f.write(self.logfile+", "+plate[-1]+"\n")
        self.evaluate_logfile()
        return

