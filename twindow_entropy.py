from music21 import *
from sets import *
import csv
import pickle
import numpy
import os
import operator
from string import Template
import numpy
import collections

"""
Primarily in-process modifications of existing, functional code
Do them here so I don't fuck up the ones that work
"""

def getProbsFromFreqs(DictionaryOfTallies):
    totalSum = 0.0
    dictOfProbs = {}
    for key, freq in DictionaryOfTallies.iteritems():
        totalSum += float(freq)
    for key, freq in DictionaryOfTallies.iteritems():
        dictOfProbs[key] = float(freq)/totalSum
    return dictOfProbs
        
def pickleExplorer():
    theSlices = pickle.load( open ('1122MajModeSliceDictwSDB.pkl', 'rb') )
    sliceTally = {}
    for i, slicey in enumerate(theSlices):
        if slicey == ['start'] or slicey == ['end']:
            continue
        theKey = slicey['key']
        theTonic = str(theKey).split(' ')[0]
        theMode = str(theKey).split(' ')[1]
        theKeyPC = pitch.Pitch(theTonic).pitchClass
        keyTransPCs = [(n - theKeyPC)%12 for n in slicey['pcset']]
        rightChord = chord.Chord(sorted(keyTransPCs))
        rightLabel = rightChord.pitchNames
        try:
            sliceTally[str((rightLabel, slicey['bassSD']))] += 1
        except KeyError:
            sliceTally[str((rightLabel, slicey['bassSD']))] = 1
    sorted_sliceTally = sorted(sliceTally.iteritems(), key=operator.itemgetter(1), reverse=True)
    xmaj = csv.writer(open('MajModeSliceTally.csv', 'wb'))
    for pair in sorted_sliceTally:
        xmaj.writerow([pair[0],pair[1]])
        
 
 
import midi
import music21
from imghdr import what
import os
import numpy
from string import Template
import csv
import operator
import scipy.stats


path = 'C:/Users/Andrew/Documents/DissNOTCORRUPT/MIDIunquant/'
listing = os.listdir(path)
#testFile = 'C:/Users/Andrew/Documents/DissNOTCORRUPT/MIDIQuantized/Alex_1_1.mid'
#testFile = 'C:/Users/Andrew/Documents/DissNOTCORRUPT/MIDIQuantized/Julian_5_6.mid'

"""
OK, things to do:
1. Strip out tracks which contain no notes (DONE)
2. From the remaining tracks, determine the number of milli(micro?)secs per tick (DONE)
3. Get a list of the note event in absolute ticks (DONE)
4. Translate those absolute ticks into elapsed milli/microseconds (DONE)
5. Figure out the distribution of note lengths; choose a good one for windowing (SKIPPED)
6. Make a list of time slices in which we can look for notes (DONE)
7. Export time slices as a csv.  Mimic ycac? (DONE)
8. Now, go back and figure out how to make the windows overlapping. (DONE)
"""

'''
TO CHANGE
For each window, whenever a pitch appears, weight it by its duration in the count
So look for the noteOff after a given noteOn, and subtract their absTicks
Counts need integers, so try #pitches x int(round(millisecs)), maybe?
'''
def midiTimeWindows(windowWidth,incUnit,solos=all):
    #windowWidth is obvious; incUnit how large the window slide step is
    #numTunes = 0
    #numShortTracks = 0
    #numTracks = 0
    #if solos != all:
        #listing = [solos]
    #we'll make a list: [millisecs at end of window, music21 chord, set of midi numbers,  pcs in order, file name]
    msandmidi = []
    for n, testFile in enumerate(listing):
        if solos != all:
            if testFile != solos:
                continue
        print path + testFile
        #if n > 50:
            #continue
            #break
        #numTunes += 1
        #for use with import midi
        pattern = midi.read_midifile(path + testFile)
        #this line makes each tick count cumulative
        pattern.make_ticks_abs()
        #print pattern.resolution, testFile
        #print len(pattern)
        for i,track in enumerate(pattern):
            #numTracks += 1
            if len(track) < 50:
                #numShortTracks += 1
                continue
            #how many tempo events?
            tempEvents = 0
            noteEvents = 0
            for thing in track:
                #print thing
                if thing.__class__ == midi.events.NoteOnEvent:
                    noteEvents += 1
                if thing.__class__ == midi.events.SetTempoEvent:
                    microspt = thing.get_mpqn() / pattern.resolution
                    #print microspt
                    tempEvents +=1
            if noteEvents == 0:
                #numShortTracks += 1
                continue
            if tempEvents == 0:
                microspt = 500000 / pattern.resolution
            if tempEvents > 1:
                print 'hey, extra tempo event?'
                break
            #windowWidth = 100 #number of milliseconds wide each bin will be
            windows = []
            #Generate a window starting at each incUnit until last window exceeds track end
            startTime = 0
            #print track[-1]
            while startTime + windowWidth < track[-1].tick* microspt/1000:
                windows.append(collections.Counter())
                startTime += incUnit
            for m, thing in enumerate(track):
                #Now put each event into all the right windows
                #if m > 50:
                    #break
                absTicks = thing.tick * microspt/1000
                if thing.__class__ == midi.events.NoteOnEvent and thing.get_velocity() != 0:
                    #figure out how long it is by looking for off event
                    for s in range(m,len(track)):
                        if track[s].__class__ == midi.events.NoteOnEvent and track[s].get_velocity() == 0 and track[s].get_pitch() == thing.get_pitch():
                            endTick = track[s].tick* microspt/1000
                            diffTicks = endTick - absTicks
                            break
                        if track[s].__class__ == midi.events.NoteOffEvent and track[s].get_pitch() == thing.get_pitch():
                            endTick = track[s].tick* microspt/1000
                            diffTicks = endTick - absTicks
                            break
                        if s == len(track):
                            print 'No note end!',testFile
                    for j in range(len(windows)):
                        #weight considering four cases.  First, if the note off starts and ends inside the first window
                        if j*incUnit < absTicks < j*incUnit + windowWidth:
                            if endTick < j*incUnit + windowWidth:
                                windows[j][thing.get_pitch()] += int(round(diffTicks))
                            #next, if it starts in one and stretches to some future window
                            if endTick > j*incUnit + windowWidth:
                                windows[j][thing.get_pitch()] += int(round(j*incUnit + windowWidth - absTicks))
                        if j*incUnit > absTicks:
                            #if it started in some past window and ends in some future one
                            if endTick > j*incUnit + windowWidth:
                                windows[j][thing.get_pitch()] += windowWidth
                            #and last: if it started in some past window and ends in this one
                            if j*incUnit < endTick < j*incUnit + windowWidth:
                                windows[j][thing.get_pitch()] += int(round(endTick - j*incUnit))
                        #Once the note has ended, stop looking for places to stick it
                        if j*incUnit > endTick:
                            break
            for j in range(len(windows)):
                if sum(windows[j].values()) == 0:#skip the empty windows
                    continue
                '''
                pitchClasses = set([])
                for mid in windows[j]:
                    if windows[j][mid] == 0:
                        continue
                    if mid%12 in pitchClasses:
                        continue
                    pitchClasses.add(mid%12)
                '''
                msandmidi.append([(j)*incUnit,windows[j]])
    #print msandmidi
    #package up a csv
    #print msandmidi
    '''
    #package up a csv
    fieldnames = ['ms window end','weighted MIDI','ordered PCs','file']
    fileName = Template('$siz $inc ms inc 1122.csv')
    csvName = fileName.substitute(siz = str(windowWidth), inc = str(incUnit))
    file = open(csvName, 'wb')
    lw = csv.writer(file)
    lw.writerow(fieldnames)
    for row in msandmidi:
        lw.writerow(row)
    '''
    return msandmidi


def entrop(solo=all):
    #go from 50ms to 60*1000 ms by doubling
    windowSize = 25
    EntropyatSize = []
    while windowSize < 60000:
        windowSize = windowSize*2
        print windowSize
        if windowSize <= 1000:
            incUnit = 25
        elif 1000 < windowSize < 10000:
            incUnit = 250
        else:
            incUnit = 1000
        if solo != all:
            msandmidi = midiTimeWindows(windowSize, incUnit, solos=solo)
        else:
            msandmidi = midiTimeWindows(windowSize,incUnit)
        entropies = []
        for i, row in enumerate(msandmidi):
            if i == 0:
                continue
            pcVector = []
            for j in range(12):
                pcVector.append(0.1)
            for mid, counts in row[1].iteritems():
                pcVector[mid%12] += counts
            #print pcVector, scipy.exp2(scipy.stats.entropy(pcVector,base=2))
            entropies.append(scipy.exp2(scipy.stats.entropy(pcVector,base=2)))
            #print windowSize,pcVector, entropies[-1]
        EntropyatSize.append([windowSize,scipy.average(entropies)])
        #now write the body of the table
    if solo != all:
        fileName = Template('$sol overlap window pc avg ent.csv')
        csvName =fileName.substitute(sol = solo.split('.')[0])
    else:
        csvName ='overlap window pc avg entropy.csv'
    file = open(csvName, 'wb')
    lw = csv.writer(file)
    for row in EntropyatSize:
        lw.writerow(row)
        
def slidingEntropy(solo,windowSize, incUnit):
    """
    GOAL: input solo and windowSize; outputs entropy of pc vector as window increments
    """
    msandmidi  = midiTimeWindows(windowSize, incUnit, solos = solo)
    entropies = []
    for i, row in enumerate(msandmidi):
        if i == 0:
            continue
        pcVector = []
        for j in range(12):
            pcVector.append(0.01)
        for mid, counts in row[1].iteritems():
            pcVector[mid%12] += counts
        entropies.append([row[0],scipy.exp2(scipy.stats.entropy(pcVector,base=2))])
    fileName = Template('$sol overlap window pc ent.csv')
    csvName =fileName.substitute(sol = solo.split('.')[0])
    file = open(csvName, 'wb')
    lw = csv.writer(file)
    for row in entropies:
        lw.writerow(row)
           
#midiTimeWindows(2000, 25, solos='Alex_6_6_blueingreen.mid')
entrop()
#slidingEntropy('Alex_6_6_blueingreen.mid', 1000, 25)
