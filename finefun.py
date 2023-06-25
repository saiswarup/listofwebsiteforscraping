# -*- coding: cp1252 -*-
import os, sys
import re
import shutil
import sys
import io
from collections import OrderedDict
import urllib
import gzip
import datetime
from imp import reload
from sys import platform
from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
import time
import requests
import json
import gc
from textblob import TextBlob
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from lxml.html.soupparser import fromstring
############Make the directory in python27 directory Name:  BrowersDriver and put geckodriver.exe in BrowersDriver directory##########
geckoPath = r'Users\saiswarupsahu\freelance\levisauctionshouse\geckodriver.exe'
###########################################################################

####################Lamda Functions##################
getFirstName = lambda x: " ".join(x[0:-1])
getLastName = lambda x,y: x[y]
checkArtistYearPatternSpace = lambda x: re.findall('(.*?)(\d{4} - \d{4})',x)
checkArtistYearPattern = lambda x: re.findall('(.*?)(\d{4}-\d{4})',x) #This check the artist name and start year and end year
checkArtistBirthPattern = lambda x: re.findall('(.*?)(b.\d{4})',x.lower()) #This check the artist name and birth with b.
yearExtract = lambda x: re.findall('(\d{4})', x)
checkDigitData = lambda x: re.findall(r"\([ /,.A-Za-z0-9_-]+\)", x)
X = lambda x : " ".join(x.replace(",","").replace('"',"").splitlines()) #This function remove coma and new lines
#######################################################

scraperDirectory = {
                "artron": "artron-scrape"
              
}

materialDict = {"material": r'\bOil\b|\bpaper\b|\bcanvas\b|\bcolour reproduction\b|\blithograph\b|\blithographs\b|\bwoodblock\b'
                            r'|\boil\b|\boils\b|\betching\b|\betchings\b|\bwatercolor\b|\bwatercolour\b|\bgraphite\b|\bboard\b|\bpanel\b|\bbronze\b|\bmetal\b'
                            r'|\bgraphite\b|\bchine\b|\bceramic\b|\bglazed\b|\bprint\b|\bprints\b|\bceramics\b|\bceramic\b|\bgilt bronze\b'
                            r'|\bsilver\b|\brosewood\b|\bwalnut\b|\bwood\b|\bearthanware\b|\bporcelain\b|\bglass\b'
                            r'|\bmixed\b|\bserigraph\b|\bvellum\b|\bink\b|\bpen\b|\bin colours\b|\bgouache\b'
                            r'|\bcolors\b|\bengraving\b|\bsolarized\b|\bphotographie.\b|\bphotographie\b|\bcorten\b'
                            r'|\bmarble\b|\bphotograph\b|\bscreenprint\b|\bacrylic\b|\bplywood\b|\bin color\b'
                            r'|\bengraved\b|\bengine\b|\bgrille\b|\bcardboard\b|\bplastic\b|\bterracotta\b|\bsilk\b|\biron\b'
                            r'|\bblack marble\b|\bbrass\b|\bplaster\b|\bfabric\b|\bpapier\b|\bcarton\b|\btoile\b'
                            r'|\bon vellum\b|\bdry point\b|\bon cover\b|\bsilkscreen\b|\blithographic\b'
                            r'|\blithographed\b|\bdry-point\b|\bplexiglas\b|\bphotolithography\b|\bbronzes\b'
                            r'|\bcollograph\b|\b collograph\b|\blitograph\b|\baquatint\b'
                            r'|\blitography\b|\bposters\b|\bplexiglass\b|\bsilkscreened\b|\bchromogenic\b|\boval\b'
                            r'|\bengravings\b|\bcolor offsets\b|\boilcloth\b|\bstone painting\b|\bblack stone\b'
                            r'|\bmourlot\b|\bbrooch\b|\bcolor offset\b|\bserigraphs\b|\bresin\b|\blithography\b'
                            r'|\bpolyester\b|\bretro\b|\bpolished\b|\bcharcoal\b|\benamel\b|\bstainless\b'
                            r'|\bwool\b|\bet\b|\bnoyer\b|\bcéramique\b|\bc\xc3\xa9ramique\b|\bbois\b|\bpalissandre\b|\bblack and white\b'
                            r'|\bpeuplier\b|\bséquoia\b|\bs\xc3\xa9quoia\b|\bcyprès\b|\bcypr\xc3\xa9s\b'
                            r'|\bcarta\b|\btela\b|\briproduzione del colore\b|\blitografia\b|\blitografie\b|\bblocco di legno\b'
                            r'|\bolio\b|\boli\b|\bacquaforte\b|\bincisioni\b|\bacquerello\b|\bgrafite\b|\btavola\b|\bpannello\b|\bbronzo\b|\bmetallo\b'
                            r'|\bgrafite\b|\bporcellana\b|\bceramica\b|\bsmaltato\b|\bstampare\b|\bstampe\b|\bceramica\b|\bapplica il bronzo\b'
                            r'|\bargento\b|\bpalissandro\b|\bnoce\b|\blegna\b|\bterracotta\b|\bporcellana\b|\bbicchiere\b'
                            r'|\bmisto\b|\bserigrafia\b|\bpergamena\b|\binchiostro\b|\bpenna\b|\ba colori\b|\bguazzo\b'
                            r'|\bcolori\b|\bincisione\b|\bsolarizzata\b|\bfotografia\b'
                            r'|\bmarmo\b|bfotografia\b|\bstampa schermo\b|\bacrilico\b|\bcompensato\b'
                            r'|\binciso\b|\bmotore\b|\bgriglia\b|\bcartone\b|\bplastica\b|\bferro\b'
                            r'|\bmarmo nero\b|\bottone\b|\bgesso\b|\btessuto\b|\bcarta\b|\btela\b'
                            r'|\bsu pergamena\b|\bpunto asciutto\b|\bin copertina\b|\bserigrafia\b|\blitografica\b|\bposter per\b'
                            r'|\blitografata\b|\bplexiglas\b|\bfotolitografia\b|\bbronzi\b'
                            r'|\bcollograph\b|\blitografia\b|\bacquatinta\b'
                            r'|\bmanifesti\b|\bserigrafato\b|\bcromogenico\b|\bovale\b'
                            r'|\boffset di colore\b|\btela cerata\b|\bpittura su pietra\b|\bpietra nera\b'
                            r'|\bmourlot\b|\bspilla\b|\bcolore sfalsato\b|\bserigrafie\b|\bresina\b'
                            r'|\bpoliestere\b|\bretrò\b|\blucidato\b|\bmatita\b|\bcarbone\b|\bsmalto\b|\binossidabile\b'
                            r'|\blana\b|\bscommessa\b|\bbianco e nero\b'
                            r'|\breproduction des couleurs\b|\blithographier\b|\blithographies\b|\bbloc de bois\b'
                            r'|\bpétrole\b|\bhuiles\b|\bgravure\b|\bgravures\b|\baquarelle\b|\bplanche\b|\bpanneau\b|\bmétal\b'
                            r'|\bcéramique\b|\bvitré\b|\bimpression\b|\bestampes\b|\bbronze doré\b|\bargent\b'
                            r'|\bbois de rose\b|\bfaïence\b|\bporcelaine\b|\bverre\b|\bmixte\b'
                            r'|\bsérigraphie\b|\bvélin\b|\bencre\b|\bstylo\b|\ben couleurs\b'
                            r'|\bcouleurs\b|\bsolarisé\b|\bmarbre\b'
                            r'|\bphotographier\b|\bimpression décran\b|\bacrylique\b|\bcontre-plaqué\b|\ben couleur\b'
                            r'|\bgravé\b|\bmoteur\b|\bpapier carton\b|\bplastique\b|\bterre cuite\b|\ble fer\b'
                            r'|\bmarbre noir\b|\blaiton\b|\bplâtre\b|\ben tissu\b'
                            r'|\bsur vélin\b|\bpoint sec\b|\ben couverture\b|\bsérigraphie\b'
                            r'|\blithographique\b|\baffiche pour\b|\blithographié\b'
                            r'|\bphotolithographie\b|\baquatinte\b|\baffiches\b|\bplexiglas\b'
                            r'|\bchromogène\b|\bdécalages de couleur\b|\btoile cirée\b'
                            r'|\bpeinture sur pierre\b|\bpierre noire\b|\bbroche\b'
                            r'|\boffset de couleur\b|\bsérigraphies\b|\brésine\b|\blithographie\b'
                            r'|\brétro\b|\bbrillant\b|\bcrayon\b|\bcharbon\b|\bémail\b'
                            r'|\binoxydable\b|\bla laine\b|\bnoir et blanc\b'
                            r'|\bpapier-\b|\bpapier\b|\bversilbert\b|\bkeramik\b'
                            r'|\bsegeltuch\b|\bfarbwiedergabe\b|\blithographien\b|\bholzblock\b|\bÖl\b|\bol\b'
                            r'|\böl\b|\böle\b|\bole\b|\bradierung\b|\bradierungen\b|\baquarell\b|\bgraphit\b|\btafel\b'
                            r'|\bmetall\b|\bbronze-\b|\bglasiert\b|\bdrucken\b|\bdrucke\b|\bvergoldet\b|\bsilber-\b'
                            r'|\bsilber-\b|\brosenholz\b|\bnussbaum\b|\bholz\b|\bsteingut\b|\bporzellan\b|\bglas\b'
                            r'|\bgemischt\b|\bsiebdruck\b|\bpergament\b|\btinte\b|\bstift\b|\bin farben\b|\bfarben\b'
                            r'|\bgravur\b|\bsolarisiert\b|\bfotografie.\b|\bfotografie\b|\bmarmor\b|\bfoto\b'
                            r'|\bacryl-\b|\bacryl\b|\bsperrholz\b|\bin farbe\b|\bgraviert\b|\bmotor\b|\bgitter\b|\bkarton\b'
                            r'|\bkunststoff\b|\bterrakotta\b|\beisen\b|\bschwarzer marmor\b|\bmessing-\b|\bmessing\b'
                            r'|\bgips\b|\bstoff\b|\bkarton\b|\bauf pergament\b|\btrockener punkt\b|\bauf dem cover\b'
                            r'|\blithographisch\b|\bplakat für\b|\bplakat fur\b|\blithographiert\b|\btrockenpunkt\b'
                            r'|\bbronzen\b|\baquatinta\b|\bchromogen\b|\bgravuren\b|\bfarboffsets\b|\bwachstuch\b'
                            r'|\bsteinmalerei\b|\bschwarzer stein\b|\bmourlot\b|\bbrosche\b|\bharz\b|\bpoliert\b'
                            r'|\bbleistift\b|\bholzkohle\b|\bemaille\b|\brostfrei\b|\bwolle\b|\bLeinwand\b|\bwoodcut\b|\bminiature\b|\baffiche\b|\bcotton\b|\bgicl\b|\blithographie\b|\bstoneware\b|\blithography\b|\bdrawing\b|\bpastel\b|\bpointe\b|\bsteel\b'}

artistQualifier_List = ['circle of', 'style of', 'manner of', 'follower of', 'school of', "attributed to", "after",
                        "cercle de", "style de", "maniere de", "adepte de", "ecole de", "attribue a", "apres", "attribuei ai","attribua a",
                        "kreis von", "art von", "anhanger von", "schule der", "zugeschrieben", "nach dem"]

httpHeaders = {
    'User-Agent': r'Mozilla/5.0 (X11; Linux i686) AppleWebKit/535.19 (KHTML, like Gecko) Chrome/18.0.1025.162 Safari/535.19',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8', 'Accept-Language': 'en-US,en;q=0.8',
    'Accept-Encoding': 'gzip,deflate,sdch', 'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
    'Connection': 'keep-alive'}

class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def http_error_302(self, req, fp, code, msg, headers):
        infourl = urllib.response.addinfourl(fp, headers, req.get_full_url())
        infourl.status = code
        infourl.code = code
        return infourl

    http_error_300 = http_error_302
    http_error_301 = http_error_302
    http_error_303 = http_error_302
    http_error_307 = http_error_302

no_redirect_opener = urllib.request.build_opener(urllib.request.HTTPHandler(), urllib.request.HTTPSHandler(),
                                              NoRedirectHandler())  # ... and this is the "abnormal" one.
opener = urllib.request.build_opener(urllib.request.HTTPHandler(), urllib.request.HTTPSHandler()) 
debug_opener = urllib.request.build_opener(urllib.request.HTTPHandler(debuglevel=1))

def decodeGzippedContent(encoded_content):
    response_stream = io.BytesIO(encoded_content)
    decoded_content = ""
    try:
        gzipper = gzip.GzipFile(fileobj=response_stream)
        decoded_content = gzipper.read()
    except: # Maybe this isn't gzipped content after all....
        decoded_content = encoded_content
    decoded_content = decoded_content.decode('utf-8', 'ignore')
    return(decoded_content)

############This function return Page Soup Object#########################
def get_soup(pageUrl, httpHeaders = {}):
    #gc.collect()
    pageRequest = urllib.request.Request(pageUrl, None, httpHeaders)
    try:
        pageResponse = opener.open(pageRequest)
        headers = pageResponse.info()
        while 'Location' in headers.keys():
            requestUrl = headers["Location"]
            #print(requestUrl)
            if requestUrl == "/home.html":
                requestUrl = pageUrl+"home.html/"
            else:
                requestUrl = requestUrl
            pageRequest = urllib.request.Request(requestUrl, None, httpHeaders)
            try:
                pageResponse = opener.open(pageRequest)
                headers = pageResponse.info()
            except:
                break
    except:
        pageResponse = None
        print("Error in get_soup: %s"%sys.exc_info()[1].__str__())
        return pageResponse

    if pageResponse is None:
        return None
    else:
        pageContent = decodeGzippedContent(pageResponse.read())
        #print(pageContent)
        pageSoup = BeautifulSoup(pageContent, features="html.parser")
        #gc.collect()
        return pageSoup
###########################################################################################

def writeHeader(fp,auction_name,auction_location,auction_date,auction_title,auctionId,lotCount,lot_sold_in):
    titles=["auction_house_name","auction_location","auction_num","auction_start_date","auction_end_date","auction_name"
           ,"lot_num","sublot_num","price_kind","price_estimate_min","price_estimate_max","price_sold","artist_name","artist_birth",
            "artish_death","artist_nationallity","artwork_name",
            "artwork_year_identifier","artwork_start_year","artwork_end_year","artwork_materials","artwork_category","artwork_markings",
            "artwork_edition","artwork_description","artwork_measurements_height","artwork_measurements_width","artwork_measurements_depth",
            "artwork_size_notes","auction_measureunit","artwork_condition_in","artwork_provenance","artwork_exhibited","artwork_literature",
            "artwork_images1","artwork_images2","artwork_images3","artwork_images4","artwork_images5",
            "image1_name","image2_name","image3_name","image4_name","image5_name","lot_origin_url"]
    fp.write(','.join(titles))
    fp.write('\n')
#######################This Function download the image#####################

###############This Function Create the Directory and send the file path#################
def getDataFilename(scrapperName,auctionId):
    basepath = "/Users/saiswarupsahu/freelance/"
    scrappernNameBase = scrapperName.split('.')[0];
    datafile = basepath + scrappernNameBase + "_" + auctionId + ".csv"
    return datafile
###########################################################################################

##################This Function Check for duplicate words from two variable if duplicate found it remove and send the unique###########
"""
Ex
material = oil on canvas
description = oil on canvas Valley Vista with Wildflowers
description = removeDupli(material,description)
if we call this function it will remove the oil on canvas from description
"""
def removeDupli(firstData,seconData):
    a = firstData.lower().split()
    b = seconData.lower().split()

    x = OrderedDict.fromkeys(a)
    y = OrderedDict.fromkeys(b)

    for k in x:
        if k in y:
            x.pop(k)
            y.pop(k)

    if y.keys().__len__() > 1:
        signature = " ".join(y.keys())
        return signature
    elif y.keys().__len__() == 1:
        try:
            signature = y.keys()[0]
            return signature
        except:
            pass
    else:
        return ""
############################################################################

#############This function get the first and last name##################
def getFisrtLastName(nameData):
    nameData = nameData.split()
    #print(nameData,"BBBBBBBBBBBBbb")
    firstName = ""
    lastName = ""
    if nameData.__len__() == 2:
        firstName = getLastName(nameData, 0)
        lastName = getLastName(nameData, 1)
    if nameData.__len__() > 2:
        firstName = getFirstName(nameData)
        lastName = getLastName(nameData, -1)
    if nameData.__len__() == 1:
        firstName = getLastName(nameData, 0)
        lastName = ""
    return firstName,lastName
################################################################

#######################Gets Dimension's ##################
def getDimansionPart(h):
    #print(h)
    h = h.split(' ')
    height = 0
    try:
        for num in h:
            if not num:
                continue
            elif '/' in num:
                numerator, denominator = num.split('/')
                num = float(numerator) / int(denominator)
            else:
                num = int(num)
            height += num
        h = str(height)
        return h
    except:
        return "0"

def getDimaision(dim):
    d = dim.replace(".","99999999").replace(",","").replace("x"," ").replace("/","05123450").split(" ")
    dimList = []
    height = "0"
    width = "0"
    depth = "0"
    size = ""
    for rrr in d:
        s = ''.join([i for i in rrr if i.isdigit()])
        if s.__len__() != 0:
            dimList.append(s.replace("99999999",".").replace("05123450","/"))
    for line in dimList:
        if "/" in line:
            index = dimList.index(line)
            dimList[dimList.index(dimList[index-1])] = getDimansionPart(dimList[index-1] +" "+ line)
            dimList[index] = ""
    dimList = filter(None,dimList)
    if dimList.__len__() != 0:
        dimaisionList = dimList
        if dimaisionList.__len__() == 3 or dimaisionList.__len__() > 3:
            height = dimaisionList[0]
            width = dimaisionList[1]
            depth = dimaisionList[2]
            size = height + " x " + width + " x " + depth
        if dimaisionList.__len__() == 2:
            height = dimaisionList[0]
            width = dimaisionList[1]
            depth = "0"
            size = height + " x " + width
        if dimaisionList.__len__() == 1:
            height = dimaisionList[0]
            width = "0"
            depth = "0"
            size = height
        return height,width,depth,size
    else:
        return "0","0","0","",None
#########################################################

############To get start Year End year or birth year death year#######################
def getStartEndYear(yearData):
    yearList = yearExtract(yearData)
    startYear = ""
    endYear = ""
    if yearList.__len__() == 2:
        startYear = yearList[0]
        endYear = yearList[1]
    if yearList.__len__() == 1:
        startYear = yearList[0]
        endYear = ""
    return startYear,endYear
###############################################################

###############This function check the date is not exceed the current year############
def checkYear(year):
    now = datetime.datetime.now()
    if str(now.year) >= year:
        if year > "1700":
            return year
        else:
            return ""
    else:
        return ""
############################################################################

def startYearEndYearCheck(startYear,endYear):
    if endYear > startYear:
        diff = int(endYear) - int(startYear)
        if diff < 10:
            return startYear,endYear
        else:
            return "",""
    else:
        return startYear,""

###########This function check the name from the material List is find then return the material#############
def getMaterial(descriptionList):
    try:
        materialList = [x for x in descriptionList if re.search(
                            materialDict["material"],
                        x.lower()) and yearExtract(
                        x).__len__() == 0 and "numbered" not in x.lower() and "date" not in x.lower()
                                    and ":" not in x and "framed" not in x.lower()
                        and "cm" not in x.lower() and "marked" not in x.lower() and "sign" not in x.lower() and "label" not in x.lower()]
        material = materialList[0].strip()
        if "bronze" in material:
            material = "bronze"
        if "(" in material:
            material=material.split("(")[0].strip()
        return material
    except:
        return ""
#########################################################################################################################

############This function return the signature######################
def getSignature(descriptionList):
    try:
        signatureList = [x for x in descriptionList if
                    re.search(r"\bsignture\b|\bsigned\b|\binscribed\b|\bsign\b|\bdated\b|\bsignatures\b"
                              r"|\bmargin\b|\btitle\b|\bmarked\b|\binitialed\b|\bmodernica label\b|\bstamped\b"
                              r"|\bmonogramm\b|\bmonogrammed\b|\bmaker\b|\btraces\b|\blabel\b"
                              r"|\bunsigned\b|\btitled\b|\bnumbered\b|\bstamp\b|\blower right\b|\blower left\b|\boriginal proof\b"
                              r"|\bfirma\b|\bfirmato\b|\bdata\b|\binscritto\b|\bcartello\b|\bdatato\b|\bfirme\b"
                              r"|\bmargine\b|\btitolo\b|\bsegnato\b|\bsiglato\b|\betichetta modernica\b|\btimbrato\b"
                              r"|\bmonogramma\b|\bcreatore\b|\borme\b|\betichetta\b|\btitolato\b|\bnumerato\b|\bfrancobollo\b|\bin basso a destra\b|\bin basso a sinistra\b|\bprova originale\b"
                              r"|\bsignature\b|\bsignée\b|\bsigné\b|\brendez-vous amoureux\b|\binscrit\b|\bsigne\b|\bdaté\b|\bles signatures\b"
                              r"|\bmarge\b|\btitre\b|\bmarqué\b|\bparaphé\b|\blabel modernica\b|\btimbré\b"
                              r"|\bmonogramme\b|\bmonogrammé\b|\bfabricant\b|\bétiquette\b"
                              r"|\btitré\b|\bnuméroté\b|\btimbre\b|\ben bas à droite\b|\ben bas à gauche\b|\bpreuve originale\b"
                              r"|\bbezeichnet\b"
                              r"\bunterschrift\b|\bunterzeichnet\b|\bdatum\b|\beingeschrieben\b|\bschild\b|\bdatiert\b|\bsignaturen\b"
                              r"|\bspanne\b|\btitel\b|\bmarkiert\b|\bparaphiert\b|\bmodernica-etikett\b|\bgestempelt\b"
                              r"|\bmonogrammiert\b|\bhersteller\b|\btraces\b|\betikette\b|\bsignee\b"
                              r"|\bbetitelt\b|\bnummeriert\b|\bbriefmarke\b|\brechts unten\b|\bunten links\b|\bunsigned\b|\bSigned\b|\bsignerad\b|\boriginalnachweis\b", x.lower())
                    and "date made" not in x.lower() and "date cr" not in x.lower() and "date of" not in x.lower() and "designed" not in x.lower()
                    and "provenance" not in x.lower() and "condition" not in x.lower()]
        if signatureList.__len__() == 1:
            signature = signatureList[0].strip()
        elif signatureList.__len__() > 1:
            signature = "; ".join(signatureList).strip()
        return signature
    except:
        return ""
###################################################################

###########This function return the edition Of data####################
"""
Ex
signature = signed 5/12
then it will return 5 of 12
"""
def getEditionOf(signature):
    if "/" in signature:
        v = signature.split("/")
    try:
        d = v[0].strip().split()
        if d[-1].isdigit():
            vv = v[1].strip().split()[0]
            edition = d[-1] + " of " + vv
            return edition
    except:
        return ""
#####################################################################

######################################This function Return the artist First Last name and birth and death year#####################
def getArtistFirstLastNameBirthDeathYear(descriptionList):
    artist_1_firstname,artist_1_lastname,artist_1_birthyear,artist_1_deathyear = "","","",""
    try:
        full_nameList = [x for x in descriptionList if "(" in x and yearExtract(x).__len__() != 0]
        full_name = full_nameList[0].strip()
    except:
        full_name = None
    if full_name:
        nameList = full_name.split("(")
        if nameList.__len__() > 1:
            artist_1_firstname, artist_1_lastname = getFisrtLastName(nameList[0])
            artist_1_birthyear, artist_1_deathyear = getStartEndYear(nameList[1])
    return artist_1_firstname,artist_1_lastname,artist_1_birthyear,artist_1_deathyear
#####################################################################################

###########This function check for the qualifier is there or not#################
def checkQualifier(artist_1_firstname,artist_1_lastname):
    name = artist_1_firstname +" "+ artist_1_lastname
    #print(name)
    artist_1_qualifier = ""
    try:
        for a in artistQualifier_List:
            if a in name.lower():
                artist_1_qualifier = a
                nameList = getFisrtLastName(name.lower().replace(artist_1_qualifier,
                                                                       "").strip())
                if nameList.__len__() != 0:
                    artist_1_firstname, artist_1_lastname = nameList
                    artist_1_firstname = artist_1_firstname.strip().title()
                    artist_1_lastname = artist_1_lastname.strip().title()
                else:
                    artist_1_lastname = ""
                    artist_1_firstname = ""
        return artist_1_firstname, artist_1_lastname,artist_1_qualifier
    except:
        return "","",""
###########################################################################################

############Return Sub Lot###################
"""
if 102A
then it will return 102 as a lot number
and A as a sub Lot
"""
def getSubLot(lot_num):
    if lot_num.__len__() != 0 or lot_num != "":
        try:
            if lot_num[-1].isalpha() == True:
                sub_lot = lot_num[-1]
                lot_num = lot_num.replace(sub_lot, "")
                return lot_num,sub_lot
        except:
            pass
###################################################################

def check_dimension_dots(size,height,width,depth):
    if size.__len__() == 0:
        size = ""
        height = "0"
        width = "0"
        depth = "0"
    if "." in width and width.__len__() == 1:
        size = height
        width = "0"
        depth = "0"
    if "." in depth and depth.__len__() == 1:
        size = height +" x "+ width
        height = height
        width = width
        depth = "0"
    if "." in height and height.__len__() == 1:
        size = ""
        height = "0"
        width = "0"
        depth = "0"
    return size,height,width,depth

def getDynamicSiteSoup(requestUrl):
    if "win" in str(platform).lower():
        # driver = webdriver.Firefox(executable_path=geckoPath)
        driver = webdriver.PhantomJS()
    else:
        from pyvirtualdisplay import Display

        # from selenium.common.exceptions import TimeoutException
        display = Display(visible=0, size=(800, 600))
        display.start()
        driver = webdriver.PhantomJS(service_args=['--cookies-file=/tmp/cookies.txt', '--ignore-ssl-errors=true', '--ssl-protocol=any'])
        # driver.set_page_load_timeout(100)
    # try:
    driver.get(requestUrl) # load the web page
    # except TimeoutException:
    #     driver.quit()# closes the driver
    #     if "win" not in str(platform).lower():
    #         display.stop()
    try:
        time.sleep(4)
        src = driver.page_source # gets the html source of the page
        parser = BeautifulSoup(src, features="html.parser") # initialize the parser and parse the source "src"
        driver.quit()# closes the driver
        if "win" not in str(platform).lower():
            display.stop()
        return parser
    except:
        pass


def getDynamicSiteSoupOnClick(request_url, click_function_name):
    if "win" in str(platform).lower():
        #print( str(platform))
        # driver = webdriver.Firefox(executable_path=geckoPath)
        # driver = webdriver.Firefox(executable_path=r"C:\Python27\Scripts\geckodriver.exe")
        driver = webdriver.PhantomJS(executable_path=r"C:\Python27\Scripts\phantomjs-2.1.1-windows\bin\phantomjs.exe")
    else:
        #print( str(platform))
        from pyvirtualdisplay import Display
        display = Display(visible=0, size=(800, 600))
        display.start()
        driver = webdriver.PhantomJS(service_args=['--cookies-file=/tmp/cookies.txt', '--ignore-ssl-errors=true', '--ssl-protocol=any'])
    driver.get(request_url) # load the web page
    from selenium.webdriver.support.wait import WebDriverWait
    try:
        element = WebDriverWait(driver, 10).until(
        lambda x: x.find_element_by_link_text(click_function_name).click())
    except:
        pass
    try:
        time.sleep(4)
        src = driver.page_source # gets the html source of the page
        parser = BeautifulSoup(src, features="html.parser") # initialize the parser and parse the source "src"
        driver.quit()# closes the driver
        if "win" not in str(platform).lower():
            display.stop()
        return parser
    except:
        pass


def replaceDotRangeTwoThreeFour(descriptionData):
    try:
        descriptionDotList = [(x,x.replace(".","")) for x in [x for x in descriptionData.split() if x.__len__() == 2
                                                              or x.__len__() == 3 or x.__len__() == 4] if "." in x]
        for i in descriptionDotList:
            if i[0] in descriptionData:
                descriptionData = descriptionData.replace(i[0],i[1])
        return descriptionData
    except:
        return descriptionData

def getCondition(descriptionList):
    try:
        conditionList = [x for x in descriptionList if "framed" in x.lower() or "good" in x.lower() or "giltwood" in x.lower() or "unframed" in x.lower()
                         or "incorniciato" in x.lower() or "bene" in x.lower() or "senza cornice" in x.lower()
                         or "encadré" in x.lower() or "bien" in x.lower() or "bois doré" in x.lower()or "condition" in x.lower() or "sans cadre" in x.lower()]
        if conditionList.__len__() > 1:
            condition = " ".join(conditionList).strip()
        else:
            condition = conditionList[0].strip()
        return condition
    except:
        return ""
        pass

def translatToEnglish(text_to_trans):
    try:
        translator = Translator()
        translated = translator.translate(text_to_trans)
        return translated.text
    except:
        try:
            chinese_blob = TextBlob(text_to_trans)
            return str(chinese_blob.translate(to='en'))
        except:
            print("Error: %s"%sys.exc_info()[1].__str__())


def getDynamicDataSoupByClassName(requestUrl,class_name):
    # display = Display(visible=0, size=(800, 600))
    # display.start()
    if "win" in str(platform).lower():
        driver = webdriver.Firefox(executable_path= geckoPath)
    else:
        from pyvirtualdisplay import Display

        # from selenium.common.exceptions import TimeoutException
        display = Display(visible=0, size=(800, 600))
        display.start()
        driver = webdriver.PhantomJS(service_args=['--cookies-file=/tmp/cookies.txt', '--ignore-ssl-errors=true', '--ssl-protocol=any'])
    # driver = webdriver.Firefox()
    driver.get(requestUrl) # load the web page
    from selenium.webdriver.support.wait import WebDriverWait
    try:
        element = WebDriverWait(driver, 10).until(
        lambda x: x.find_element_by_class_name(class_name))
    except:
        pass
    time.sleep(4)
    src = driver.page_source # gets the html source of the page
    parser = BeautifulSoup(src, features="html.parser") # initialize the parser and parse the source "src"
    driver.quit()# closes the driver
    # display.stop()
    return parser

def remove_tags(text):
        TAG_RE = re.compile(r'<[^>]+>')
        try:
            return TAG_RE.sub('', text).strip()
        except:
            return text

def checkArtistPattern(artistName):
    try:
        your_string = artistName.replace("*","").strip().title()
        trans = checkDigitData(translatToEnglish(your_string))[0]
        yearData = yearExtract(trans)
        return yearData
    except:
        return None

def requestPageJson(pageUrl):
    headers = {'User-Agent': 'Mozilla/5.0  Gecko/20100101 Firefox/55.0', 'Accept':'application/json, text/plain, */*','Connection':'keep-alive'}
    req = requests.get(pageUrl, headers=headers)
    if str(req) == "<Response [400]>":
        headers = {r'User-Agent': 'Rigor API Tester', 'Accept':'application/json, text/plain, */*','Connection':'keep-alive'}
        req = requests.get(pageUrl, headers=headers)
    pageResponse = req.text
    pageContent = json.loads(pageResponse)
    return pageContent

def getDynamicPageDataCss(requestUrl):
    # display = Display(visible=0, size=(800, 600))
    # display.start()
    if "win" in str(platform).lower():
        driver = webdriver.PhantomJS()
    else:
        from pyvirtualdisplay import Display

        # from selenium.common.exceptions import TimeoutException
        display = Display(visible=0, size=(800, 600))
        display.start()
        driver = webdriver.PhantomJS(service_args=['--cookies-file=/tmp/cookies.txt', '--ignore-ssl-errors=true', '--ssl-protocol=any'])
    # driver = webdriver.Firefox()
    driver.get(requestUrl) # load the web page
    from selenium.webdriver.support.wait import WebDriverWait
    try:
        # element = WebDriverWait(driver, 10).until(
        # lambda x: x.find_element_by_class_name("ng-scope"))
        wait = WebDriverWait(driver, 10)
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "a.ng-scope")))
    except:
        pass
    src = driver.page_source # gets the html source of the page
    parser = BeautifulSoup(src, features="html.parser") # initialize the parser and parse the source "src"
    driver.quit()# closes the driver
    # display.stop()
    return parser

def getDynamicSiteSoupPageDown(pageUrl,pagedown_limit,counter):
    try:
        if "win" in str(platform).lower():
            browser = webdriver.Firefox(executable_path=geckoPath)
        else:
            from pyvirtualdisplay import Display

            # from selenium.common.exceptions import TimeoutException
            display = Display(visible=0, size=(800, 600))
            display.start()
            browser = webdriver.PhantomJS(service_args=['--cookies-file=/tmp/cookies.txt', '--ignore-ssl-errors=true', '--ssl-protocol=any'])
        browser.get(pageUrl)
        time.sleep(1)

        elem = browser.find_element_by_tag_name("body")
        #1000000
        no_of_pagedowns = pagedown_limit

        while no_of_pagedowns:
            elem.send_keys(Keys.PAGE_DOWN)
            # time.sleep(0.2)
            no_of_pagedowns-=counter

        src = browser.page_source
        parser = BeautifulSoup(src, features="html.parser")
        browser.quit()
        return parser
    except:
        return ""

def getJsonData(textValue_str):
    # textValue = str([x for x in v[0]][0])
    try:
        jsonValue = '{%s}' % (textValue_str.split('{', 1)[1].rsplit('}', 1)[0],)
        value = json.loads(jsonValue)
        return value
    except:
        return ""
