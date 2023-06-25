# -*- coding: cp1252 -*-
from finefun import *
import subprocess
import os, sys, re, time, gzip
import csv
from tempfile import NamedTemporaryFile
import shutil
import logging
import subprocess
import io
import urllib
from urllib.parse import urlencode, quote_plus
import html
from cryptography.fernet import Fernet
import unidecode


htmlTagPattern = re.compile(r"<[^>]+>", re.MULTILINE | re.DOTALL)
htmlEntitiesDict = {'，':',','&#9313;':'','&#9312;':'','&emsp;':'','&#201;':'e','&nbsp;' : ' ', '&#160;' : ' ', '&amp;' : '&', '&#038;' : '&', '&lt;' : '<', '&#60;' : '<', '&gt;' : '>', '&#62;' : '>', '&apos;' : '\'', '&#39;' : '\'', '&quot;' : '"', '&#34;' : '"', '&#8211;' : '-', '&euro;' : 'Euro' }

httpHeaders = { 'User-Agent' : r'Mozilla/5.0 (X11; Linux i686) AppleWebKit/535.19 (KHTML, like Gecko) Chrome/18.0.1025.162 Safari/535.19',  'Accept' : 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8', 'Accept-Language' : 'en-US,en;q=0.8', 'Accept-Encoding' : 'gzip,deflate,sdch', 'Accept-Charset' : 'ISO-8859-1,utf-8;q=0.7,*;q=0.3', 'Connection' : 'keep-alive'}


def stripHtmlEntities(content):
    for entityKey in htmlEntitiesDict.keys():
        entityKeyPattern = re.compile(entityKey)
        content = re.sub(entityKeyPattern, htmlEntitiesDict[entityKey], content)
    return content
def stripHTML(dataitem):
    dataitem = re.sub(htmlTagPattern, "", dataitem) # stripped off all HTML tags...
    # Handle HTML entities...
    for entity in htmlEntitiesDict.keys():
        dataitem = dataitem.replace(entity, htmlEntitiesDict[entity])
    return(dataitem)


class Scrape:
    def __init__(self,auctionId,mainUrl,imagepath, downloadImages,fp):
        self.auctionId = auctionId
        self.mainUrl = mainUrl
        self.domainUrl = "https://www.ader-paris.fr"
        self.downloadImages = downloadImages
        self.imagepath = imagepath
        self.fp = fp
        self.run()


    def formatDate(cls, datestr):
        if not datestr or datestr == "":
            return ""
        mondict = {'Janvier' : 'Jan', 'Février' : 'Feb', 'Mars' : 'Mar', 'Avril' : 'Apr', 'Mai' : 'May', 'Juin' : 'Jun', 'Juillet' : 'Jul', 'Août' : 'Aug', 'Septembre' : 'Sep', 'Octobre' : 'Oct', 'Novembre' : 'Nov', 'Décembre' : 'Dec'}
        datestrcomponents = datestr.split(" ")
        if datestrcomponents.__len__() < 3:
            return ""
        dd = datestrcomponents[0]
        mon = datestrcomponents[1].capitalize()
        year = datestrcomponents[2]
        monstr = mon
        if mon in mondict.keys():
            monstr = mondict[mon]
        retdate = dd + "-" + monstr + "-" + year
        return retdate

    formatDate = classmethod(formatDate)

    def encryptFilename(self, filename):
        k = Fernet.generate_key()
        f = Fernet(k)
        encfilename = f.encrypt(filename.encode())
        return encfilename


    def run(self):
        nextPage = True
        soup = get_soup(self.mainUrl)
        self.writeHeaders(soup)#Write the header part of csv
        beginspacePattern = re.compile("^\s+")
        endspacePattern = re.compile("\s+$")
        bdPattern1 = re.compile("(\d{4})\-(\d{4})")
        try:
            auction_location = soup.find("div", {'class': 'lieu_vente'}).getText().replace(',', ' ')
            auction_location = beginspacePattern.sub("", auction_location)
        except:
            pass
        titlePattern = re.compile("(.*)\-\s+Ader", re.IGNORECASE)
        if not soup:
            return ""
        auctitletags = soup.find_all("title")
        title = ""
        if auctitletags.__len__() > 0:
            titletext = auctitletags[0].renderContents().decode('utf-8')
            tps = re.search(titlePattern, titletext)
            if tps:
                title = tps.groups()[0]
        datedivtags = soup.find_all("div", {'class' : 'date_vente'})
        auctiondate = ""
        if datedivtags.__len__() > 0:
            datecontents = datedivtags[0].renderContents().decode('utf-8')
            datecontents = datecontents.replace("\n", "").replace("\r", "")
            datecontents = beginspacePattern.sub("", datecontents)
            datePattern = re.compile("(\d{1,2})\s+([^\d]+)\s+(\d{4})\s+")
            dps = re.search(datePattern, datecontents)
            if dps:
                dd = dps.groups()[0]
                mon = dps.groups()[1]
                yy = dps.groups()[2][2:]
                auctiondate = "%s-%s-%s"%(dd, mon, yy)
        #auctiondate = self.__class__.formatDate(auctiondate)
        brPattern = re.compile("<br\s*\/>", re.IGNORECASE)
        provenancePattern = re.compile("Provenance\s*\:", re.IGNORECASE)
        exhibitionPattern = re.compile("Exposition\s*\:", re.IGNORECASE)
        literaturePattern = re.compile("Bibliographie\s*\:", re.IGNORECASE)
        artworkyearPattern = re.compile("([\w\séî]+)\:\s*(\d{4})")
        enddotPattern = re.compile("\.\s*$")
        yearPattern = re.compile("(\d{4})")
        while nextPage:
            productDetails = soup.findAll("div", {"class": "product-desc"})
            for product in productDetails:
                auction_house_name="Ader"
                auction_location=""
                auction_num=str(self.auctionId)
                auction_start_date=auctiondate
                auction_end_date=auctiondate
                auction_name=title
                lot_num=""
                sublot_num=""
                price_kind=""
                price_estimate_min=""
                price_estimate_max=""
                price_sold="0"
                artist_name=""
                artist_birth=""
                artish_death=""
                artist_nationallity=""
                artwork_name=""
                artwork_year_identifier=""
                artwork_start_year=""
                artwork_end_year=""
                artwork_materials=""
                artwork_category=""
                artwork_markings=""
                artwork_edition=""
                artwork_description=""
                artwork_measurements_height=""
                artwork_measurements_width=""
                artwork_measurements_depth=""
                artwork_size_notes=""
                auction_measureunit=""
                artwork_condition_in=""
                artwork_provenance=""
                artwork_exhibited=""
                artwork_literature=""
                artwork_images1=""
                artwork_images2=""
                artwork_images3=""
                artwork_images4=""
                artwork_images5=""
                image1_name=""
                image2_name=""
                image3_name=""
                image4_name=""
                image5_name=""
                lot_origin_url=""
                try:
                    artwork_images1 = product.find_previous_sibling('div').find('img')['src']
                    image1_name=artwork_images1.split('/')[-1]
                except:
                    print("Error parsing image URL: %s"%sys.exc_info()[1].__str__())
                try:
                    auction_location = soup.find("div", {'class': 'lieu_vente'}).getText().replace(',', ' ')
                    auction_location = beginspacePattern.sub("", auction_location)
                except:
                    print("Error parsing auction location: %s"%sys.exc_info()[1].__str__())
                aTag = product.find("a")
                if aTag:
                    detailPageUrl = self.domainUrl + aTag["href"]
                    detailPageUrl = detailPageUrl.replace('"', "")
                    lot_origin_url=detailPageUrl
                    try:
                        detailPageSoup = get_soup(detailPageUrl)
                    except:
                        detailPageSoup = None
                        print("Error creating details page soup: %s"%sys.exc_info()[1].__str__())
                    try:
                        lot_num = detailPageSoup.find("span", {"class": "fiche_lot_num"}).getText().strip()
                    except:
                        print("Error getting lot number: %s"%sys.exc_info()[1].__str__())
                    detailPageList = None
                    try:
                        detailPageContents = detailPageSoup.find_all("div", {"class": "fiche_lot_description"})[0].renderContents().decode('utf-8')
                        detailPageList = re.split(brPattern, detailPageContents)
                    except:
                        print("Error getting lot description on details page: %s"%sys.exc_info()[1].__str__())
                    if not detailPageList or detailPageList.__len__() == 0:
                        continue
                    try:
                        artistFirstName,artistLastName,artistBirthDeath,artistBirthYear,artistDeathYear='','','','',''
                        if artistFirstName == '':
                            artistNameBirthDeath = detailPageList[0]
                            scrapNameBirthDeath = stripHTML(str(artistNameBirthDeath))
                            if artistNameBirthDeath != None:
                                if '(' in artistNameBirthDeath:
                                    artistNameBirthDeathParts = stripHTML(str(artistNameBirthDeath)).split('(')
                                    artistName = str(artistNameBirthDeathParts[0])
                                    artistBirthDeath = str(artistNameBirthDeathParts[1])
                                else:
                                    artistName = scrapNameBirthDeath
                                    nameTitleMatch = re.search("([A-Z\s]+)\s(.*)\s(Aquarelle|Gouache|Relief.*)\.?(.*)",
                                                               artistName)
                                    if nameTitleMatch:
                                        artistName = nameTitleMatch.group(1)
                                        artworkTitle = nameTitleMatch.group(2)
                                        if nameTitleMatch.group(3) != None:
                                            material = nameTitleMatch.group(3)
                                        if nameTitleMatch.group(4) != None:
                                            signedBy = nameTitleMatch.group(4).strip()
                                artistName = beginspacePattern.sub("", artistName)
                                #print(artistName)
                                namePattern = re.compile(r"(.*)\s(\w+)", re.MULTILINE | re.DOTALL)
                                matchName = namePattern.match(artistName)
                                if matchName:
                                    artistFirstName = str(matchName.group(1)).title().strip()
                                    if str(matchName.group(2)).title() != None:
                                        artistLastName = str(matchName.group(2)).title().strip()
                                    else:
                                        artistLastName = ""
                                else:
                                    artistFirstName = artistName.title()

                                artistBirthDeathPattern = re.compile(r".*(\d{4})(\/|\-)(\d{2,4}).*",
                                                                     re.MULTILINE | re.DOTALL)
                                artistBirthDeathPattern2 = re.compile(r"(.*)\s(\d+)\)", re.MULTILINE | re.DOTALL)

                                matchartistBirthDeathPattern = artistBirthDeathPattern.match(artistBirthDeath)
                                matchartistBirthDeathPattern2 = artistBirthDeathPattern2.match(artistBirthDeath)

                                if matchartistBirthDeathPattern:
                                    artistBirthYear = str(matchartistBirthDeathPattern.group(1))
                                    artistDeathYear = str(matchartistBirthDeathPattern.group(3))
                                if matchartistBirthDeathPattern2:
                                    artistBirthYear = str(matchartistBirthDeathPattern2.group(2))
                        artist_birth = artistBirthYear
                        artish_death = artistDeathYear
                        artist_name=artistFirstName+" "+artistLastName
                        #print(artist_name + " ## " + artist_birth + " ## " + artish_death)
                    except:
                        pass
                    print("lotNum:-%s"%lot_num)
                    try:
                        lot_num, sublot_num = getSubLot(lot_num)
                    except:
                        pass
                    try:
                        dimPartList = [x for x in detailPageList if "cm" in x]
                        unitPattern = re.compile("\s+(\w{2})\s*$")
                        numericPattern = re.compile("^[\d\s\.,]+$")
                        if dimPartList.__len__() >= 1:
                            dimPartList[0] = dimPartList[0].replace("'", "").replace("\n", "").replace("\r", "")
                            ups = re.search(unitPattern, dimPartList[0])
                            if ups:
                                auction_measureunit = ups.groups()[0]
                            else:
                                auction_measureunit = "cm"
                            dimPartList[0] = dimPartList[0].replace(auction_measureunit, "")
                            dimensionList = dimPartList[0].split("x")
                            #dimensionList = getDimaision(dimPartList[0])
                            artwork_measurements_height = dimensionList[0]
                            artwork_measurements_height = beginspacePattern.sub("", artwork_measurements_height)
                            artwork_measurements_height = endspacePattern.sub("", artwork_measurements_height)
                            if not re.search(numericPattern, artwork_measurements_height):
                                artwork_measurements_height = ""
                            artwork_size_notes = artwork_measurements_height
                            if dimensionList.__len__() > 1:
                                artwork_measurements_width = dimensionList[1]
                                artwork_measurements_width = beginspacePattern.sub("", artwork_measurements_width)
                                artwork_measurements_width = endspacePattern.sub("", artwork_measurements_width)
                                artwork_size_notes += 'x' + artwork_measurements_width
                                if not re.search(numericPattern, artwork_measurements_width):
                                    artwork_measurements_width = ""
                            if dimensionList.__len__() > 2:
                                artwork_measurements_depth = dimensionList[2]
                                artwork_measurements_depth = beginspacePattern.sub("", artwork_measurements_depth)
                                artwork_measurements_depth = endspacePattern.sub("", artwork_measurements_depth)
                                artwork_size_notes += 'x' + artwork_measurements_depth
                                if not re.search(numericPattern, artwork_measurements_depth):
                                    artwork_measurements_depth = ""
                            artwork_size_notes = endspacePattern.sub("", artwork_size_notes)
                            artwork_size_notes += " " + auction_measureunit
                            #print(artwork_size_notes)
                    except:
                        print(sys.exc_info()[1].__str__())
                    try:
                        artworkName = detailPageSoup.find("h1", {"class": "fiche_titre_lot"}).title().strip()
                    except:
                        pass
                    try:
                        estimatePriceDiv = detailPageSoup.find("div", {"class": "estimAff4"})
                    except:
                        estimatePriceDiv = None
                        pass
                    if estimatePriceDiv:
                        try:
                            priceList = estimatePriceDiv.getText().replace("Estimate", "").replace("&euro;",
                                                                                                   "").replace(
                                " ", "").strip()
                            priceList = re.sub('[A-Za-z]', '', priceList).split("-")
                            if priceList.__len__() == 2:
                                price_estimate_min = X(priceList[0].strip()).replace("€", "").strip()
                                price_estimate_max = X(priceList[1].strip()).replace("€", "").strip()
                            if priceList.__len__() == 1:
                                price_estimate_min = X(priceList[0].strip()).replace("€", "").strip()
                                price_estimate_max = "0"
                        except:
                            pass
                    try:
                        price_sold=detailPageSoup.find("div",{"class":"fiche_lot_resultat"}).getText().strip()
                        price_sold=''.join((re.findall('\d',price_sold)))
                        print (price_sold),"price  sold"
                    except:
                        pass
                    if price_sold != "0":
                        price_kind = "price realized"
                    elif price_estimate_min != '0' or price_estimate_max != '0':
                        price_kind = 'estimate'
                    else:
                        price_kind = "unknown"
                    artwork_description = detailPageSoup.find("div", {"class": "fiche_lot_description"}).getText()
                    print(artwork_description.split('\n'))
                   
                    try:
                        descriptiontext = detailPageSoup.find_all("div", {"class": "fiche_lot_description"})[0].renderContents().decode('utf-8')
                    except:
                        descriptiontext = ""
                    descparts = re.split(brPattern, descriptiontext)
                    artwork_description = htmlTagPattern.sub("", artwork_description)
                    artwork_description = beginspacePattern.sub("", artwork_description)
                    artwork_description = artwork_description.replace('"', "").replace("'", "")
                    artwork_materials = getMaterial(detailPageList)
                    artwork_markings = getSignature(detailPageList)
                    if type(artwork_markings) == str:
                        artwork_markings = artwork_markings.replace('"', "").replace("'", "")
                        artwork_markings = artwork_markings.replace(",", ":")
                    artwork_edition = getEditionOf(artwork_markings)
                    if type(artwork_edition) == str:
                        artwork_edition = artwork_edition.replace('"', "").replace("'", "")
                        artwork_edition = artwork_edition.replace(",", ":")
                    pflag, eflag, lflag = 0, 0, 0
                    plist = []
                    elist = []
                    llist = []
                    for descpart in descparts:
                        descpart = descpart.replace(",", ":")
                        descpart = descpart.replace("'", "").replace('"', "")
                        if re.search(provenancePattern, descpart):
                            pflag = 1
                            eflag, lflag = 0, 0
                        if re.search(exhibitionPattern, descpart):
                            eflag = 1
                            pflag, lflag = 0, 0
                        if re.search(literaturePattern, descpart):
                            lflag = 1
                            pflag, eflag = 0, 0
                        if pflag == 1:
                            plist.append(descpart)
                        if eflag == 1:
                            elist.append(descpart)
                        if lflag == 1:
                            llist.append(descpart)
                        """
                        yps = re.search(artworkyearPattern, descpart)
                        if yps and (not artwork_name or artwork_name == ""):
                            artwork_start_year = yps.groups()[1]
                            artwork_name = yps.groups()[0]
                            print(artwork_name)
                        """
                    if (not artwork_name or artwork_name == "") and descparts.__len__() > 1:
                        artwork_name = descparts[1]
                    artwork_name = re.compile("^\s*\)\s*", re.DOTALL).sub("", artwork_name)
                    yps = re.search(yearPattern, artwork_name)
                    if yps:
                        artwork_start_year = yps.groups()[0]
                        artwork_name = yearPattern.sub("", artwork_name)
                    artwork_name = enddotPattern.sub("", artwork_name)
                    partmaterialPattern = re.compile("(Oil)|(Gouache)|(Ink)|(Watercolour)|(Acrylic)|(Sculpture)|(Pastel)|(Print)|(Lithograph)\s*$")
                    mps = re.search(partmaterialPattern, artwork_name)
                    if mps:
                        material = mps.groups()[0]
                        if material is not None:
                            artwork_materials = material + " " + artwork_materials
                            artwork_name = partmaterialPattern.sub("", artwork_name)
                    artwork_provenance = ";".join(plist)
                    artwork_exhibited = ";".join(elist)
                    artwork_literature = ";".join(llist)
                    artwork_provenance = beginspacePattern.sub("", artwork_provenance)
                    artwork_exhibited = beginspacePattern.sub("", artwork_exhibited)
                    artwork_literature = beginspacePattern.sub("", artwork_literature)
                    if type(artwork_edition) == str:
                        artwork_edition = artwork_edition.replace('"', "'")
                    processedArtistName = artist_name.replace(" ", "_")
                    processedArtistName = unidecode.unidecode(processedArtistName)
                    processedArtworkName = artwork_name.replace(" ", "_")
                    processedArtworkName = unidecode.unidecode(processedArtworkName)
                    processedAuctionTitle = auction_name.replace(" ", "_")
                    sublot_number = ""
                    #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + auction_num + "__" + lot_num + "__" + sublot_num
                    newname1 = auction_num + "__" + processedArtistName + "__" + lot_num + "_a"
                    #encryptedFilename = self.encryptFilename(newname1)
                    encryptedFilename = newname1
                    encryptedFilename = str(encryptedFilename).replace("b'", "")
                    encryptedFilename = str(encryptedFilename).replace("'", "")
                    image1_name = str(encryptedFilename) + ".jpg"

                    price_estimate_min = str(price_estimate_min).replace(",", "").replace(" ", "")
                    price_estimate_max = str(price_estimate_max).replace(",", "").replace(" ", "")
                    price_sold = str(price_sold).replace(",", "").replace(" ", "")
                    a=artwork_description.split('\n')
                    artwork_materials = getMaterial(a)
                    a2 = [x for x in a if " cm" in x.lower()  ]      
                    artwork_markings=a[2].replace(",",'')         
                    
                    print(artwork_materials)
                    try:
                        dimPartList = [x for x in artwork_description.split('\n') if "cm" in x]
                        unitPattern = re.compile("\s+(\w{2})\s*$")
                        numericPattern = re.compile("^[\d\s\.,]+$")
                        if dimPartList.__len__() >= 1:
                            dimPartList[0] = dimPartList[0].replace("'", "").replace("\n", "").replace("\r", "")
                            ups = re.search(unitPattern, dimPartList[0])
                            if ups:
                                auction_measureunit = ups.groups()[0]
                            else:
                                auction_measureunit = "cm"
                            dimPartList[0] = dimPartList[0].replace(auction_measureunit, "")
                            dimensionList = dimPartList[0].split("x")
                            #dimensionList = getDimaision(dimPartList[0])
                            artwork_measurements_height = dimensionList[0]
                            artwork_measurements_height = beginspacePattern.sub("", artwork_measurements_height)
                            artwork_measurements_height = endspacePattern.sub("", artwork_measurements_height)
                            if not re.search(numericPattern, artwork_measurements_height):
                                artwork_measurements_height = ""
                            artwork_size_notes = artwork_measurements_height
                            if dimensionList.__len__() > 1:
                                artwork_measurements_width = dimensionList[1]
                                artwork_measurements_width = beginspacePattern.sub("", artwork_measurements_width)
                                artwork_measurements_width = endspacePattern.sub("", artwork_measurements_width)
                                artwork_size_notes += 'x' + artwork_measurements_width
                                if not re.search(numericPattern, artwork_measurements_width):
                                    artwork_measurements_width = ""
                            if dimensionList.__len__() > 2:
                                artwork_measurements_depth = dimensionList[2]
                                artwork_measurements_depth = beginspacePattern.sub("", artwork_measurements_depth)
                                artwork_measurements_depth = endspacePattern.sub("", artwork_measurements_depth)
                                artwork_size_notes += 'x' + artwork_measurements_depth
                                if not re.search(numericPattern, artwork_measurements_depth):
                                    artwork_measurements_depth = ""
                            artwork_size_notes = endspacePattern.sub("", artwork_size_notes)
                            artwork_size_notes += " " + auction_measureunit
                            print(artwork_size_notes)
                    except:
                        print(sys.exc_info()[1].__str__())
                    yps = re.search(artworkyearPattern, descpart)
                    if yps and (not artwork_name or artwork_name == ""):
                        artwork_start_year = yps.groups()[1]
                        artwork_name = yps.groups()[0]
                       
                    titledetails=detailPageSoup.find("div", {"class": "fiche_titre_lot"}).getText().strip()
                    try:
                        artistFirstName,artistLastName,artistBirthDeath,artistBirthYear,artistDeathYear='','','','',''
                        if artistFirstName == '':
                            artistNameBirthDeath = titledetails
                            scrapNameBirthDeath = stripHTML(str(artistNameBirthDeath))
                            if artistNameBirthDeath != None:
                                if '(' in artistNameBirthDeath:
                                    artistNameBirthDeathParts = stripHTML(str(artistNameBirthDeath)).split('(')
                                    artistName = str(artistNameBirthDeathParts[0])
                                    artistBirthDeath = str(artistNameBirthDeathParts[1])
                                else:
                                    artistName = scrapNameBirthDeath
                                    nameTitleMatch = re.search("([A-Z\s]+)\s(.*)\s(Aquarelle|Gouache|Relief.*)\.?(.*)",
                                                               artistName)
                                    if nameTitleMatch:
                                        artistName = nameTitleMatch.group(1)
                                        artworkTitle = nameTitleMatch.group(2)
                                        if nameTitleMatch.group(3) != None:
                                            material = nameTitleMatch.group(3)
                                        if nameTitleMatch.group(4) != None:
                                            signedBy = nameTitleMatch.group(4).strip()
                                artistName = beginspacePattern.sub("", artistName)
                                #print(artistName)
                                namePattern = re.compile(r"(.*)\s(\w+)", re.MULTILINE | re.DOTALL)
                                matchName = namePattern.match(artistName)
                                if matchName:
                                    artistFirstName = str(matchName.group(1)).title().strip()
                                    if str(matchName.group(2)).title() != None:
                                        artistLastName = str(matchName.group(2)).title().strip()
                                    else:
                                        artistLastName = ""
                                else:
                                    artistFirstName = artistName.title()

                                artistBirthDeathPattern = re.compile(r".*(\d{4})(\/|\-)(\d{2,4}).*",
                                                                     re.MULTILINE | re.DOTALL)
                                artistBirthDeathPattern2 = re.compile(r"(.*)\s(\d+)\)", re.MULTILINE | re.DOTALL)

                                matchartistBirthDeathPattern = artistBirthDeathPattern.match(artistBirthDeath)
                                matchartistBirthDeathPattern2 = artistBirthDeathPattern2.match(artistBirthDeath)

                                if matchartistBirthDeathPattern:
                                    artistBirthYear = str(matchartistBirthDeathPattern.group(1))
                                    artistDeathYear = str(matchartistBirthDeathPattern.group(3))
                                if matchartistBirthDeathPattern2:
                                    artistBirthYear = str(matchartistBirthDeathPattern2.group(2))
                        artist_birth = artistBirthYear
                        artish_death = artistDeathYear
                        artist_name=artistFirstName+" "+artistLastName
                        print(artist_name + " ## " + artist_birth + " ## " + artish_death)
                        if artwork_name == '':
                            artwork_name=a[0].strip()
                        print(artwork_name)
                        print(artwork_start_year)
                    except:
                        pass
                    matcatdict_en = {}
                    matcatdict_fr = {}
                    with open("/Users/saiswarupsahu/freelanceprojectchetan/docs/fineart_materials.csv", newline='') as mapfile:
                        mapreader = csv.reader(mapfile, delimiter=",", quotechar='"')
                        for maprow in mapreader:
                            matcatdict_en[maprow[1]] = maprow[3]
                            matcatdict_fr[maprow[2]] = maprow[3]
                    mapfile.close()
                    
                    materials = artwork_materials
                    materialparts = materials.split(" ")
                    catfound = 0
                    for matpart in materialparts:
                            if matpart in ['in', 'on', 'of', 'the', 'from']:
                                continue
                            try:
                                matPattern = re.compile(matpart, re.IGNORECASE|re.DOTALL)
                                for enkey in matcatdict_en.keys():
                                    if re.search(matPattern, enkey):
                                        artwork_category = matcatdict_en[enkey]
                                        catfound = 1
                                        break
                                for frkey in matcatdict_fr.keys():
                                    if re.search(matPattern, frkey):
                                        artwork_category = matcatdict_fr[frkey]
                                        catfound = 1
                                        break
                                if catfound:
                                    break
                            except:
                                pass
                    print(artwork_category)

                    try:
                        rX = lambda x: " ".join(x.replace(",", "").replace("\n", "").replace("\t", "").replace('"', "").splitlines())
                        self.fp.write('"' + rX(auction_house_name) + '","' + rX(auction_location) + '","' + rX(auction_num) + '","' + rX(auction_start_date) + '","' + rX(auction_end_date) + '","' + rX(auction_name) + '","' + rX(lot_num) + '","' + rX(sublot_num) + '","' + rX(price_kind) + '","' + rX(price_estimate_min) + '","' + rX(price_estimate_max) + '","' + rX(price_sold) + '","' + rX(artist_name) + '","'  + rX(artist_birth) + '","' + rX(artish_death) + '","' + rX(artist_nationallity) + '","' + rX(artwork_name) + '","' +  rX(artwork_year_identifier) + '","' + rX(artwork_start_year) + '","' + rX(artwork_end_year) + '","' + rX(artwork_materials) + '","' + rX(artwork_category) + '","' + rX(artwork_markings) + '","' + rX(artwork_edition) + '","' + rX(artwork_description) + '","' + rX(artwork_measurements_height) + '","' + rX(artwork_measurements_width) + '","' + rX(artwork_measurements_depth) + '","' + rX(artwork_size_notes) + '","' + rX(auction_measureunit) + '","' + rX(artwork_condition_in) + '","' + rX(artwork_provenance) + '","' + rX(artwork_exhibited) + '","' + rX(artwork_literature) + '","' + rX(artwork_images1) + '","' + rX(artwork_images2) + '","' + rX(artwork_images3) + '","' + rX(artwork_images4) + '","' + rX(artwork_images5) + '","' + rX(image1_name) + '","' + rX(image2_name) + '","' + rX(image3_name) + '","' + rX(image4_name) + '","' + rX(image5_name) + '","' + rX(lot_origin_url) + '"\n')
                    except:
                        pass
            navUrl = ""
            navigationAnchor = soup.findAll("div", {"class": "pagination_catalogue"})[0].find("a", {
                        "class": "nextLink"})

            if navigationAnchor:
                navUrl = navigationAnchor['href']
                navUrl = "https://www.ader-paris.fr/" + navUrl
            else:
                navUrl = ""
            if not navUrl or navUrl == "":
                nextPage = False
                break
            requestUrl = navUrl
            soup = get_soup(requestUrl)
            nextPage = True




    def writeHeaders(self,soup):
        auction_name, auction_date, auction_title, auction_location, lotCount, lot_sold_in = "", "", "", "", "", ""
        lot_sold_in = "EUR"
        auction_name = "Ader"
        beginspacePattern = re.compile("^\s+")
        auction_location=''
        try:
            auction_location = soup.find("div", {'class': 'lieu_vente'}).getText().replace(',', ' ')
            auction_location = beginspacePattern.sub("", auction_location)
        except:
            pass
        try:
            auction_title = soup.find("h1",{"class": "nom_vente"}).getText().replace("|","")
        except:
            pass
        try:
            auction_date=soup.findAll('div',{'class':'date_vente'})[0].getText().encode('utf8').strip()
            dateFormat=re.search(r".*(\s\d+)\s(.*)\s(\d{4}).*",auction_date)
            if dateFormat:
                month=dateFormat.group(2)
                monthDict ={"janvier": "January","f\E9vrier": "February","mars": "March","avril": "April","mai": "May","juin": "June","juillet": "July","ao\FBt": "August","septembre": "September","octobre": "October","novembre": "November","d\E9cembre": "December"}
                for entityKey in monthDict.keys():
                                        entityKeyPattern = re.compile(entityKey)
                                        month = re.sub(entityKeyPattern, monthDict[entityKey], month)
            auction_date=dateFormat.group(1)+" "+month+" "+ dateFormat.group(3)
        except:
            pass
        try:
            lotCount=soup.findAll('div',{'class':'nbre_lot_haut'})[0].getText().encode('utf8').strip()
            lotCount=''.join(re.findall('sur(.*)',lotCount)).strip()
        except:
            pass

        #print "lotCount: ", lotCount, "date: ", auction_date, "Title: ", auction_title, "AuctionLocation: ", auction_location
        writeHeader(self.fp,auction_name,auction_location,auction_date,auction_title,self.auctionId,lotCount,lot_sold_in)

    def getTextData(self,detailPageList,textName):
        try:
            textData = [item for index,item in enumerate(detailPageList) if textName in item.lower()][0]
            provenance = textData.strip().replace("\n","").replace("\r","").replace(">","")
            return provenance
        except:
            return ""

    def getIndexData(self,detailPageList,textName):
        try:
            indexNo = [index for index,item in enumerate(detailPageList) if textName in item][0]
            provenance = textName +" " + detailPageList[indexNo+1]
            provenance = provenance.strip().replace("\n","").replace("\r","")
            return provenance
        except:
            return ""

def updatestatus(auctionno, auctionurl):
    auctionurl = auctionurl.replace("%3A", ":")
    auctionurl = auctionurl.replace("%2F", "/")
    pageurl = "http://216.137.189.57:8080/scrapers/finish/?scrapername=Ader&auctionnumber=%s&auctionurl=%s&scrapertype=2"%(auctionno, urllib.parse.quote(auctionurl))
    pageResponse = None
    try:
        pageResponse = urllib.request.urlopen(pageurl)
    except:
        print ("Error: %s"%sys.exc_info()[1].__str__())  

if __name__ == "__main__":
    if sys.argv.__len__() < 5:
        print("Insufficient parameters")
        sys.exit()
    auctionurl = sys.argv[1]
    auctionnumber = sys.argv[2]
    csvpath = sys.argv[3]
    imagepath = sys.argv[4]
    downloadimages = 0
    convertfractions = 0
    if sys.argv.__len__() > 5:
        downloadimages = sys.argv[5]
    if sys.argv.__len__() > 6:
        convertfractions = sys.argv[6]
    fp = open(csvpath, "w")
    Scrape(auctionnumber, auctionurl, imagepath, downloadimages ,fp)
    fp.close()
    updatestatus(auctionnumber, auctionurl)

# Example: python ader.py "https://www.ader-paris.fr/en/catalog/93012-vente-online-tableaux-dessins-estampes-art-moderne-et-contemporain" 93012  /Users/saiswarupsahu/freelanceprojectchetan/ader_93012.csv /Users/saiswarupsahu/freelanceprojectchetan/117437 0 0


