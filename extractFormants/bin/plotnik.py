########################################################################################
##                  !!! This is NOT the original plotnik.py file !!!                  ##
##                                                                                    ##
## Last modified by Ingrid Rosenfelder:  June 1, 2010                                 ##
## - mostly comments (all comment beginning with a double pound sign ("##"))          ##
## - some closing of file objects                                                     ##
## - docstrings for all classes and functions                                         ##
## - changed order of contents:  (alphabetical within categories)                     ##
##    1. regexes & dictionaries                                                       ##
##    2. classes                                                                      ##
##    3. functions                                                                    ##
## - modified outputPlotnikFile:                                                      ##
##    + style coding                                                                  ##
##    + original LPC measurement values (poles and bandwidths)                        ##
########################################################################################

import sys
import string
import re

glide_regex = re.compile('{[a-z0-9]*}') ## Plotnik glide coding: '{[f|b|i|m|s|d|br2|g}'
style_regex = re.compile('-[0-9]-')     ## Plotnik stylistic levels:  '-[1-7]-'
comment_regex = re.compile('-- .*')     ## Plotnik:  beginning of comment
count_regex = re.compile('[0-9]$')      ## Plotnik:  number at end of token (for multiple tokens of same word):  '[0-9]+$'
stress_regex = re.compile('[0-2]$')     # Arbabet coding:  primary stress, secondary stress, or unstressed (at end of vowel)

## "TRANSLATION" DICTIONARIES:
## Arpabet to Plotnik coding
A2P = {'AA':'5', 'AE':'3', 'AH':'6', 'AO':'53', 'AW':'42', 'AY':'41', 'EH':'2', 'ER':'94', 'EY':'21', 'IH':'1', 'IY':'11', 'OW':'62', 'OY':'61', 'UH':'7', 'UW':'72'}
A2P_FINAL = {'IY':'12', 'EY':'22', 'OW':'63'}
A2P_R = {'EH':'2', 'AE':'3', 'IH':'14', 'IY':'14', 'EY':'24', 'AA':'44', 'AO':'64', 'OW':'64', 'UH':'74', 'UW':'74', 'AH':'6', 'AW':'42', 'AY':'41', 'OY':'61'}
## CMU phoneset (distinctive features) to Plotnik coding
MANNER = {'s':'1', 'a':'2', 'f':'3', 'n':'4', 'l':'5', 'r':'6'}
PLACE = {'l':'1', 'a':'4', 'p':'5', 'b':'2', 'd':'3', 'v':'6'}
VOICE = {'-':'1', '+':'2'}


class PltFile:
  """represents a Plotnik file (header and vowel measurements)"""
  ## header - speaker information
  first_name = ''           ## first name of speaker
  last_name = ''            ## last name of speaker
  age = ''                  ## speaker age
  city = ''                 ## city          
  state = ''                ## state
  sex = ''                  ## speaker sex
  ts = ''                   ## Telsur number (just the number, without "TS"/"ts")
  ## second header line
  N = ''                    ## number of tokens in file
  S = ''                    ## group log mean for nomalization (ANAE p. 39) ??? - or individual log mean ???
  ## tokens
  measurements = []         ## list of measurements (all following lines in Plotnik file)

class VowelMeasurement:
  """represents a single vowel token (one line in a Plotnik data file)"""
  F1 = 0                    ## first formant
  F2 = 0                    ## second formant
  F3 = ''                   ## third formant
  code = ''                 ## Plotnik code for vowel class (includes phonetic environment):  "xx.xxxxx"
  stress = 1                ## level of stress (default = primary) (and duration:  "x.xxx"???)
  text = ''                 ## rest of line (everything that is not numbers:  token/word, glide, style, comment, ...)
  word = ''                 ## (orthographic) transcription of token (with parentheses and count)
  trans = ''                ## normal transcription (without parentheses and count, upper case)
  fname = ''                ## 8-character token identifier???
  comment = ''              ## Plotnik comment (everything after " -- ")
  glide = ''                ## Plotnik coding for glide (if present)
  style = ''                ## Plotnik coding for stylistic level (if present)
  t = 0                     ## time of measurement


def arpabet2plotnik(ac, trans, prec_p, foll_p, phoneset):
  """translates Arpabet transcription of vowels into codes for Plotnik vowel classes"""
  ## ac = Arpabet coding
  ## trans = (orthographic) transcription of token
  ## prec_p = preceding phone
  ## foll_p = following phone
  ## phoneset = CMU phoneset (distinctive features)
  ## pc = Plotnik code
  
  ## free vs. checked vowels  -> iyF, eyF, owF:
  if foll_p == '' and ac in ['IY', 'EY', 'OW']: 
    pc = A2P_FINAL[ac]
  ## Canadian Raising -> ay0:
  elif foll_p != '' and ac == 'AY' and phoneset[foll_p].cvox == '-':
    pc = '47'
  ## ingliding ah:
  elif ac == 'AA' and trans in ['FATHER', 'MA', 'PA', 'SPA', 'CHICAGO', 'PASTA', 'BRA', 'UTAH', 'TACO', 'GRANDFATHER', "FATHER'S", "GRANDFATHER'S", 'CALM', 'PALM', 'BALM', 'ALMOND', 'LAGER', 'SALAMI', 'NIRVANA', 'KARATE']:
    pc = '43'
  ## uw after coronal onsets -> Tuw:
  elif prec_p != '' and ac == 'UW' and phoneset[prec_p].cplace == 'a':
    pc = '73'
  ## Vhr subsystem (following tautosyllabic r):
  ## (no distinction between ohr and owr)
  elif foll_p != '' and phoneset[foll_p].ctype == 'r' and ac != 'ER':
    pc = A2P_R[ac]
  ## all other cases:
  else:
    pc = A2P[ac]
  return pc

def cmu2plotnik_code(i, phones, trans, phoneset):
  """converts Arpabet to Plotnik coding (for vowels) and adds Plotnik environmental codes (.xxxxx)"""
  ## i = index of vowel in token
  ## phones = list of phones in whole token
  ## trans = transcription (label) of token
  ## phoneset = CMU phoneset (distinctive features)
  
  ## don't do anything if it's a consonant
  if not is_v(phones[i].label):
    return None, None

  ## FOLLOWING SEGMENT:
  # if the vowel is the final phone in the list, then there is no following segment
  if i+1 == len(phones):
    foll_p = ''         ## following segment:
    fm = '0'            ## - following manner (code)
    fp = '0'            ## - following place (code)
    fv = '0'            ## - following voice (code)
    fs = '0'            ## following sequence (code)
  else:
    # get the following segment, and strip the stress code off if it's a vowel
    foll_p = re.sub(stress_regex, '', phones[i+1].label)
    ctype = phoneset[foll_p].ctype
    cplace = phoneset[foll_p].cplace
    cvox = phoneset[foll_p].cvox
    # convert from the CMU codes to the Plotnik codes
    fm = MANNER.get(ctype, '0')                 ## get value for key, 
    fp = PLACE.get(cplace, '0')                 ## "0": default if key does not exist
    fv = VOICE.get(cvox, '0')                   ## from MANNER, PLACE, VOICE dictionaries above
    ## FOLLOWING SEQUENCE:
    n_foll_syl = get_n_foll_syl(i, phones)      ## number of following syllables
    n_foll_c = get_n_foll_c(i, phones)          ## number of consonants in coda
    if n_foll_c <= 1 and n_foll_syl == 1:
      fs = '1'                                  ## one following syllable
    elif n_foll_c <= 1 and n_foll_syl >= 2:
      fs = '2'                                  ## two following syllables
    elif n_foll_c > 1 and n_foll_syl == 0:
      fs = '3'                                  ## complex coda
    elif n_foll_c > 1 and n_foll_syl == 1:
      fs = '4'                                  ## complex coda + 1 syllable
    elif n_foll_c > 1 and n_foll_syl >= 2:
      fs = '5'                                  ## complex coda + 2 syllables
    else:
      fs = '0'              

  ## PRECEDING SEGMENT:
  # if the vowel is the first phone in the list, then there is no preceding segment
  if i == 0:
    prec_p = ''         ## preceding phone
    ps = '0'            ## preceding segment (code)
  else:
    # get the preceding segment, and strip the stress code off if it's a vowel
    prec_p = re.sub(stress_regex, '', phones[i-1].label)
    if prec_p in ['B', 'P', 'V', 'F']:
      ps = '1'          ## oral labial
    elif prec_p in ['M']:
      ps = '2'          ## nasal labial
    elif prec_p in ['D', 'T', 'Z', 'S', 'TH', 'DH']:
      ps = '3'          ## oral apical
    elif prec_p in ['N']:
      ps = '4'          ## nasal apical
    elif prec_p in ['ZH', 'SH', 'JH', 'CH']:
      ps = '5'          ## palatal
    elif prec_p in ['G', 'K']:
      ps = '6'          ## velar
    elif i > 1 and prec_p in ['L', 'R'] and phones[i-2] in ['B', 'D', 'G', 'P', 'T', 'K', 'V', 'F', 'Z', 'S', 'SH', 'TH']:
      ps = '8'          ## obstruent + liquid
    elif prec_p in ['L', 'R', 'ER0', 'ER2', 'ER1']:
      ps = '7'          ## liquid
    elif prec_p in ['W', 'Y']:
      ps = '9'          ## /w/, /y/
    else:
      ps = '0'

  ## convert CMU (Arpabet) transcription into Plotnik code
  ## ("label[:-1]":  without stress digit)
  code = arpabet2plotnik(phones[i].label[:-1], trans, prec_p, foll_p, phoneset)
  ## add Plotnik environmental coding
  code += '.'
  code += fm
  code += fp
  code += fv
  code += ps
  code += fs
  return code, prec_p

def convertDur(dur):
  """converts durations into integer msec (as required by Plotnik)"""
  dur = int(round(dur * 1000))
  return dur

def convertStress(stress):
  """converts labeling of unstressed vowels from '0' in the CMU Pronouncing Dictionary to '3' in Plotnik"""  
  if stress == '0':
    stress = '3'
  return stress

def get_age(line):
  """returns age of speaker from header line of Plotnik file, if present"""
  try:
    age = line.split(',')[1].strip()          ## second data field 
  except IndexError:
    age = ''
  return age

def get_city(line):
  """returns city from header line of Plotnik file, if present"""
  sex = get_sex(line)
  if sex in ['m', 'f']:                       ## if sex included as third data field, city is in forth
    try:
      city = line.split(',')[3].strip()
    except IndexError:
      city = ''
  else:                                       ## otherwise, look in third data field
    try:
      city = line.split(',')[2].strip()
    except IndexError:
      city = ''
  return city

def get_first_name(line):
  """returns first name of speaker from header line of Plotnik file"""
  first_name = line.split(',')[0].split()[0]  ## first part of first data field
  return first_name

def get_last_name(line):
  """returns last name of speaker from header line of Plotnik file, if present"""
  try:
    last_name = line.split(',')[0].split()[1] ## second part of first data field
  except IndexError:
    last_name = ''
  return last_name

def get_n(line):
  """returns number of tokens from second header line of Plotnik file, if present"""
  try:
    n = int(line.strip().split(',')[0])
  except IndexError:
    n = ''
  return n

def get_n_foll_c(i, phones):
  """returns the number of consonants in the syllable coda"""
  ## i = index of vowel phoneme in question
  ## phones = complete list of phones in word/token 
  n = 0
  for p in phones[i+1:]:
    if is_v(p.label):
      break
    elif n == 1 and p.label in ['Y', 'W', 'R', 'L']:  # e.g. 'figure', 'Wrigley', etc.
      break
    else:
      n += 1
  return n

def get_n_foll_syl(i, phones):
  """returns the number of following syllables"""
  ## number of syllables determined by number of following vowels
  ## i = index of vowel phoneme in question
  ## phones = complete list of phones in word/token
  n = 0
  for p in phones[i+1:]:
    if is_v(p.label):
      n += 1
  return n

def get_s(line):
  """returns ??? from second header line of Plotnik file, if present"""
  try:
    s = float(line.strip().split(',')[1])
  except IndexError:
    s = ''
  return s

def get_sex(line):
  """returns speaker sex from header line of Plotnik file, if included"""
  try:
    sex = line.split(',')[2].strip()          ## sex would be listed in third data field
  except IndexError:
    sex = ''
  # only some files have sex listed in the first line
  if sex not in ['m', 'f']:                   ## if contents of third data field somthing other than sex (e.g. city)
    sex = ''
  return sex

def get_state(line):
  """returns state from header line of Plotnik file, if present"""
  sex = get_sex(line)
  if sex in ['m', 'f']:                       ## if sex included as third data field, state is in fifth
    try:
      state = line.split(',')[4].strip().split()[0]
    except IndexError:
      state = ''
  else:                                       ## otherwise, look in forth data field
    try:
      state = line.split(',')[3].strip().split()[0]
    except IndexError:
      state = ''
  return state

def get_stressed_v(phones):
  """returns the index of the stressed vowel, or '' if none or more than one exist"""
  primary_count = 0
  for p in phones:
    if p[-1] == '1':
      primary_count += 1
      i = phones.index(p)
  # if there is more than vowel with primary stress in the transcription,
  ## then we don't know which one to look at, so return ''
  if primary_count != 1:
    return ''
  else:
    return i

def get_ts(line):
  """returns Telsur subject number from header line of Plotnik file, if present"""
  if ' TS ' in line:
    ts = line.strip().split(' TS ')[1]        ## returns only the number, not "TS"/"ts"
  elif ' ts ' in line:
    ts = line.strip().split(' ts ')[1]
  else:
    ts = ''
  return ts

# this is a hack based on the fact that we know that the CMU transcriptions for vowels
# all indicate the level of stress in their final character (0, 1, or 2);
# will rewrite them later to be more portable...
## this function sometimes causes index errors!
def is_v(p):
  """checks whether a given phone is a vowel (based on final code for stress from CMU dictionary)"""
  if p[-1] in ['0', '1', '2']:
    return True
  else:
    return False

def outputPlotnikFile(Plt, f):
  """writes the contents of a PltFile object to file (in Plotnik format)"""
  ## pltFields = {'f1':0, 'f2':1, 'f3':2, 'code':3, 'stress':4, 'word':5}
  fw = open(f, 'w')
  fw.write(" ".join([Plt.first_name, Plt.last_name]) + ',' + ','.join([Plt.age, Plt.sex, Plt.city, Plt.state, Plt.ts]))
  fw.write('\n')
  fw.write(str(Plt.N) + ',' + str(Plt.S))   ## no spaces around comma here!
  fw.write('\n')
  for vm in Plt.measurements:
    stress = convertStress(vm.stress)
    dur = convertDur(vm.dur)
    if not vm.f3:
      vm.f3 = ''
    fw.write(','.join([str(round(vm.f1, 1)), str(round(vm.f2, 1)), str(vm.f3), vm.code, stress + '.' + str(dur), vm.word]))
    if vm.style:  
      fw.write(' -' + vm.style+ '-')                                  ## style coding, if applicable
    fw.write(' ' + str(vm.t) + ' ')                                   ## measurement point
#    fw.write('+' + ','.join([str(p) for p in vm.poles]) + '+')        ## list of original poles as returned from LPC analysis
#    fw.write('+' + ','.join([str(b) for b in vm.bandwidths]) + '+')   ## list of original bandwidths as returned from LPC analysis
    fw.write('\n')
  fw.close()

def process_measurement_line(line):
  """splits Plotnik measurement line into values for formants, vowel class, stress, token, glide, style, and comment"""
  vm = VowelMeasurement()
  vm.F1 = float(line.split(',')[0])     ## first formant
  vm.F2 = float(line.split(',')[1])     ## second formant
  try:
    vm.F3 = float(line.split(',')[2])   ## third formant, if present
  except ValueError:
    vm.F3 = ''
  vm.code = line.split(',')[3]          ## Plotnik vowel code (includes phonetic environment):  "xx.xxxxx"
  vm.stress = line.split(',')[4]        ## stress (and duration:  "x.xxx"???)
  vm.text = line.split(',')[5]          ## rest of line (word, glide, style, comment)
                                        ## if TIME STAMP was included in file, it would be in field 6!
                                        ## -> check number of fields returned from split(',')!
  ## process text
  vm.word = vm.text.split()[0]          ## token (with parentheses and count)
  vm.trans = word2trans(vm.word)        ## translate token to normal transcription (without parentheses and count, upper case)
  vm.fname = word2fname(vm.word)        ## translate token to ???unique filename???

  res = re.findall(glide_regex, vm.text)    ## search for glide coding
  if len(res) > 0:                          ## if present:
    temp = res[0].replace('{', '')          ## get rid of initial parenthesis
    temp = temp.replace('}', '')            ## get rid of final parenthesis
    vm.glide = temp                         ## glide coding

  res = re.findall(style_regex, vm.text)    ## search for style coding
  if len(res) > 0:                          ## if present:
    temp = res[0].replace('-', '')          ## get rid of initial dash
    temp = temp.replace('-', '')            ## get rid of final dash
    vm.style = temp                         ## style coding

  res = re.findall(comment_regex, vm.text)  ## search for comment
  if len(res) > 0:                          ## if present:
    temp = res[0].replace('-- ', '')        ## get rid of initial two dashes
    vm.comment = temp                       ## why should glide only be indicated in comment, not as glide coding?
    if temp == 'glide':
      vm.glide = 'g'
  else:
    res = style_regex.split(vm.text)        ## split rest of line by style coding - WHY???
    if len(res) > 1:                        
      vm.comment = res[1].strip()           ## anything that comes after the style coding

  return vm

def process_plt_file(filename):
  """reads a Plotnik data file into a PltFile object"""
  f = open(filename, 'rU')
  line = f.readline().strip()     ## NOTE:  stripped of end-of-line character(s)! (see below)
  
  # skip initial blank lines
  while line == '':               ## stripped line empty = no content
    line = f.readline()           ## next line read - NOTE:  WITH end-of-line character(s)!
    # EOF was reached, so this file only contains blank lines
    if line == '':                ## if not even end-of-line character in next line, then end of file reached
      f.close()                   ## (added)
      sys.exit()
    else:                         ## else:  strip end-of-line characters away, 
      line = line.strip()         ## and check for content again (beginning of loop)

  Plt = PltFile()

  ## process first header line
  Plt.first_name = get_first_name(line)
  Plt.last_name = get_last_name(line)
  Plt.age = get_age(line)
  Plt.sex = get_sex(line)
  Plt.city = get_city(line)
  Plt.state = get_state(line)
  Plt.ts = get_ts(line)

  ## process second header line
  line = f.readline().strip()
  Plt.N = get_n(line)
  Plt.S = get_s(line)

  ## data lines next...
  line = f.readline().strip()

  ## again, check for blank lines:
  # skip any blank lines between header and formant measurements
  while line == '':
    line = f.readline()
    # this file only contains blank lines
    if line == '':
      f.close()                   ## (added)
      sys.exit()
    else:
      line = line.strip()

  Plt.measurements = []

  # proceed until we reach the blank line separating the formant data from the means
  while line != '':
     # some files don't contain this blank line, so look to see if the first value in the line is '1';
     # if it is, this must be the beginning of the means list, and not an F1 measurement
    if line.split(',')[0] == '1':
      break
    vm = process_measurement_line(line)
    Plt.measurements.append(vm)
    line = f.readline().strip()

  ## close file object (added by Ingrid)
  f.close()

  ## perform check on number of measurements/tokens
  if len(Plt.measurements) != Plt.N:
    print "ERROR:  N's do not match for %s" % filename
    return None
  else:
    return Plt

def word2fname(word):
  """makes a unique filename out of token name???  (limited to 8 characters, count included as final) ???"""
  fname = word.replace('(', '')           ## delete initial parenthesis
  fname = fname.replace(')', '')          ## delete final parenthesis
  fname = fname.replace('-', '')          ## delete dashes ???
  fname = re.sub(glide_regex, '', fname)  ## bug fix if space between token & glide annotation is missing?
  fname = str.upper(fname)                ## transform to upper case
  if len(fname) > 8:
    last = fname[-1]
    if last in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']:
      fname = fname[0:7] + last
    else:
      fname = fname[0:8]
  return fname

def word2trans(word):
  """converts Plotnik word as originally entered (with parentheses and token number) into normal transcription (upper case)"""
  trans = word.replace('(', '')           ## delete initial parenthesis
  trans = trans.replace(')', '')          ## delete final parenthesis
  # the glide annotation, if it exists, is outside the count, so this must be done first
  trans = re.sub(glide_regex, '', trans)  ## bug fix if space between token & glide annotation is missing?
  trans = re.sub(count_regex, '', trans)
  trans = str.upper(trans)                ## transform to upper case
  return trans