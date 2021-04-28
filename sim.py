# sim.py

import rotationtools
import matplotlib.pyplot as plt
import yaml

with open('gear.yaml') as f:
    data = yaml.safe_load(f)

weaving = 0
comp = 1
use_drums = 1
haste_pot = 1

spec = 'bm'
gearset = 'P1-BiS'

fight_length = 180

def hawk_uptime(ews):
    proc_chance = 0.1
    haste = 1.15
    duration = 12
    
    attacks_during = int(duration/ews*haste)
    
    drop_chance = 0.9**attacks_during
    cont_dur = sum([0.9**n * 0.1 * ews/1.15 * (n+1) for n in range(0,attacks_during)])
    
    mean_dur = 12 + cont_dur / (1-drop_chance)
    mean_pause = ews / proc_chance
    
    return mean_dur / (mean_dur + mean_pause)

def mean_dps(duration):
    dps_t = []
    time = []
    mhaste_t = []
    rhaste_t = []
    
    r = rotationtools.rotationplot(spec)
    r.character.gear.load(data, gearset)
    r.character.gear.addWeapon(data, 'Soulstring','RangedWeapons')
    r.character.gear.addWeapon(data, 'Mooncleaver','Twohanders')
    print('Running simulation for set {} with {} / {}.'.format(gearset, r.character.gear.rweaponname, r.character.gear.mweaponname))
    optionstr = ('Complex' if comp else 'Simple') + ' rotations. '
    optionstr = optionstr + ('Melee' if weaving else 'No') + ' weaving.'
    optionstr = optionstr + (' Permanent drums.' if use_drums else ' No drums.')
    optionstr = optionstr + (' Using haste pot with BW/TBW and trinket. ' if haste_pot else ' No haste pots.')
    print(optionstr)
    r.reloadChar()
    #print('Pet does {petdps:.0f} dps.'.format(petdps=r.character.pet.dps()))
    print()
    rotations = data['Rotations']['Weaving'] if weaving else data['Rotations']['Ranged']
    if comp:
        rotations = rotations + data['Rotations']['ComplexWeaving'] if weaving else data['Rotations']['ComplexRanged']
    haste_proc = 325 # dst 325
    haste_proc_uptime = 0.18 if r.character.gear.dst else 0
    for t in range(0,duration,1):
        time.append(t)
        haste = 1.0506 if use_drums else 1
        rapid_duration = 19 if r.character.gear.t3pc>=2 else 15
        if (t % 120)>=5 and (t % 120)<25 and haste_pot:
            haste = haste + 0.2532 # haste pot is additive with drums
        haste_from_rating = haste
        if (t % 600)>=5 and (t % 600)<45:
            haste = haste * 1.3 # bloodlust
        ranged_haste = haste * 1.15 * (1.2 if spec=='bm' else 1)
        if (t % 180)>=5 and (t % 180)<(5 + rapid_duration):
            ranged_haste = ranged_haste * 1.5 # rapid fire
            
        if (len(mhaste_t)>0) and (haste==mhaste_t[-1]) and (ranged_haste==rhaste_t[-1]) and (t % 20)!=5:
            dps = dps_t[-1] # don't need to recalc, nothing changed
        else:
            ihawk_time = hawk_uptime(3.0 / ranged_haste)
            if spec=='sv':
                ihawk_time = 0
            
            mhastes = [haste]
            rhastes = [ranged_haste]
            uptimes = []
            
            if haste_proc_uptime!=0:
                factor = (haste_from_rating + haste_proc/15.8/100) /haste_from_rating
                for n in range(0, len(mhastes)):
                    mhastes.append(mhastes[n] * factor) 
                    rhastes.append(rhastes[n] * factor)
            if ihawk_time>0:
                for n in range(0, len(mhastes)):
                    mhastes.append(mhastes[n])
                    rhastes.append(rhastes[n] * 1.15)
            
            if len(mhastes)==1:
                uptimes = [1]
            elif not haste_proc_uptime:
                uptimes = [1-ihawk_time, ihawk_time]
            elif not ihawk_time:
                uptimes = [1-haste_proc_uptime, haste_proc_uptime]
            else:
                mutual = haste_proc_uptime*ihawk_time*1.1
                uptimes = [0, haste_proc_uptime-mutual, ihawk_time-mutual, mutual] # higher simultaneous uptime of both effects
                uptimes[0] = 1 - sum(uptimes[1:]) # calculate base eWS time
                
            dps_table = []
            
            if (t % 120)>=5 and (t % 120)<25:
                r.character.gear.total_rap = r.character.gear.total_rap + 278
                r.character.gear.total_map = r.character.gear.total_map + 278
                r.change_stats()
                
            for n in range(0, len(rhastes)):
                
                # find best rotation in loop
                
                dps = 0
                
                for rot in rotations:
                    r.clear()
                    r.melee.haste = mhastes[n]
                    r.ranged.haste = rhastes[n]
                    r.change_haste()
                    r.add_rotation(rot)
                    if (t % 120)>=5 and (t % 120)<23 and spec=='bm':
                        dps_new = r.calc_dps(r.calc_dur(),1.5/1.1) * 1.1
                    else:
                        dps_new = r.calc_dps(r.calc_dur(),1)
                    if dps_new>dps:
                        dps = dps_new
                
                dps_table.append(dps)
                
                # end rotation loop
            
            if (t % 120)>=5 and (t % 120)<25:
                r.character.gear.total_rap = r.character.gear.total_rap - 278
                r.character.gear.total_map = r.character.gear.total_map - 278
                r.change_stats()
        
        weighted_dps = [dps_table[n] * uptimes[n] for n in range(0,len(dps_table))]
        
        mhaste_t.append(haste)
        rhaste_t.append(ranged_haste)
        dps_t.append(sum(weighted_dps))
        
    return time, dps_t, rhaste_t

if __name__ == "__main__":
    t, dps, rhaste = mean_dps(fight_length)
    fig, ax = plt.subplots(figsize=(10, 6), dpi=150)
    print('Total: {dps:.0f} dps'.format(dps=sum(dps)/len(dps)))
    ax.plot(t, dps)
    ax.set_xlabel('time [s]')
    ax.set_ylabel('dps')
    ax2 = ax.twinx()
    ax2.plot(t, rhaste, 'r:')
    ax2.set_ylabel('haste')
    