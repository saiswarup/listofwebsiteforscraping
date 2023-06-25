# -*- coding: utf-8 -*-
import os, sys, re
import urllib, urllib.request
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import unicodedata
import io
import gzip
import time
import simplejson as json
import datetime
import string
import requests
from requests_toolbelt.adapters.source import SourceAddressAdapter
from urllib.parse import urlencode, quote_plus
import html
import csv
import unidecode

partialUrlPattern = re.compile("^/\w+")

def decodeHtmlEntities(content):
    entitiesDict = {'&nbsp;' : ' ', '&quot;' : '"', '&lt;' : '<', '&gt;' : '>', '&amp;' : '&', '&apos;' : "'", '&#160;' : ' ', '&#60;' : '<', '&#62;' : '>', '&#38;' : '&', '&#34;' : '"', '&#39;' : "'"}
    for entity in entitiesDict.keys():
        content = content.replace(entity, entitiesDict[entity])
    return(content)


# Implement signal handler for ctrl+c here.
def setSignal():
    pass

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


def unicodefraction_to_decimal(v):
    fracPattern = re.compile("(\d*)\s*([^\s\.\,;a-zA-Z]+)")
    fps = re.search(fracPattern, v)
    if fps:
        fpsg = fps.groups()
        wholenumber = fpsg[0]
        fraction = fpsg[1]
        decimal = round(unicodedata.numeric(fraction), 3)
        if wholenumber:
            decimalstr = str(decimal).replace("0.", ".")
        else:
            decimalstr = str(decimal)
        value = wholenumber + decimalstr
        return value
    return v


class BernaertsBot(object):
    
    htmltagPattern = re.compile("\<\/?[^\<\>]*\/?\>", re.DOTALL)
    pathEndingWithSlashPattern = re.compile(r"\/$")

    htmlEntitiesDict = {'&nbsp;' : ' ', '&#160;' : ' ', '&amp;' : '&', '&#38;' : '&', '&lt;' : '<', '&#60;' : '<', '&gt;' : '>', '&#62;' : '>', '&apos;' : '\'', '&#39;' : '\'', '&quot;' : '"', '&#34;' : '"'}

    def __init__(self, auctionurl, auctionnumber):
        # Create the opener object(s). Might need more than one type if we need to get pages with unwanted redirects.
        self.opener = urllib.request.build_opener(urllib.request.HTTPHandler(), urllib.request.HTTPSHandler()) # This is my normal opener....
        self.no_redirect_opener = urllib.request.build_opener(urllib.request.HTTPHandler(), urllib.request.HTTPSHandler(), NoRedirectHandler()) # ... and this one won't handle redirects.
        #self.debug_opener = urllib.request.build_opener(urllib.request.HTTPHandler(debuglevel=1))
        # Initialize some object properties.
        self.sessionCookies = ""
        self.httpHeaders = { 'User-Agent' : r'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36',  'Accept' : '*/*', 'Accept-Language' : 'en-us,en;q=0.5', 'Accept-Encoding' : 'gzip,deflate', 'Accept-Charset' : 'ISO-8859-1,utf-8;q=0.7,*;q=0.7', 'Keep-Alive' : '115', 'Connection' : 'keep-alive', }
        self.httpHeaders['cache-control'] = "max-age=0"
        self.httpHeaders['Host'] = "www.bernaerts.eu"
        self.httpHeaders['Referer'] = auctionurl
        self.httpHeaders['upgrade-insecure-requests'] = "1"
        self.httpHeaders['sec-fetch-dest'] = "empty"
        self.httpHeaders['sec-fetch-mode'] = "cors"
        self.httpHeaders['sec-fetch-site'] = "same-origin"
        self.httpHeaders['sec-fetch-user'] = "?1"
        self.httpHeaders['X-Requested-With'] = "XMLHttpRequest"
        self.homeDir = os.getcwd()
        self.auctionurl = auctionurl
        catalognumberPattern = re.compile("veil=([^\&]+)\&")
        cnps = re.search(catalognumberPattern, auctionurl)
        self.catalognumber = ""
        if cnps:
            self.catalognumber = cnps.groups()[0]
        else:
            print("Could not find catalog number")
            sys.exit()
        #https://www.bernaerts.eu/tags/komende_ajax.php?cookie=&cataloog=%s&zitting=7&sql_sort_method=0&start_page=0&sql_lot_range=63x21&lijst=0&search_mode=&search_data=&verkocht=00
        self.requestUrl = "https://www.bernaerts.eu/tags/veiling_ajax.php?cookie=&cataloog=c1085&zitting=3&sql_sort_method=0&start_page=0&show_rows=150&sql_lot_range=&lijst=0&search_mode=&search_data=&verkocht=1"#%self.catalognumber
        parsedUrl = urlparse(self.requestUrl)
        print(self.requestUrl)
        self.baseUrl = parsedUrl.scheme + "://" + parsedUrl.netloc + "/"
        #print(self.requestUrl)
        self.pageRequest = urllib.request.Request(self.requestUrl, headers=self.httpHeaders)
        self.pageResponse = None
        self.requestMethod = "GET"
        self.postData = {}
        try:
            self.pageResponse = self.opener.open(self.pageRequest)
            headers = self.pageResponse.getheaders()
            #print(headers)
            if "Location" in headers:
                self.requestUrl = headers["Location"]
                self.pageRequest = urllib.request.Request(self.requestUrl, headers=self.httpHeaders)
                try:
                    self.pageResponse = self.no_redirect_opener.open(self.pageRequest)
                except:
                    print ("Couldn't fetch page due to limited connectivity. Please check your internet connection and try again. %s"%sys.exc_info()[1].__str__())
                    sys.exit()
        except:
            print ("Couldn't fetch page due to limited connectivity. Please check your internet connection and try again. %s"%sys.exc_info()[1].__str__())
            sys.exit()
        self.httpHeaders["Referer"] = self.requestUrl
        self.sessionCookies = self.__class__._getCookieFromResponse(self.pageResponse)
        self.httpHeaders["Cookie"] = self.sessionCookies
        # Initialize the account related variables...
        self.currentPageContent = self.__class__._decodeGzippedContent(self.getPageContent())
        self.currentPageNumber = 1 # Page number of the page that is currently being read.
        self.data = {'auction_house_name': '', 'auction_location' : '', 'auction_num' : '', 'auction_start_date' : '', 'auction_end_date' : '', 'auction_name' : '', 'lot_num' : '', 'sublot_num' : '', 'price_kind' : '', 'price_estimate_min' : '', 'price_estimate_max' : '', 'price_sold' : '', 'artist_name' : '', 'artist_birth' : '', 'artist_death' : '', 'artist_nationality' : '', 'artwork_name' : '', 'artwork_year_identifier' : '', 'artwork_start_year' : '', 'artwork_end_year' : '', 'artwork_materials' : '', 'artwork_category' : '', 'artwork_markings' : '', 'artwork_edition' : '', 'artwork_description' : '', 'artwork_measurements_height' : '', 'artwork_measurements_width' : '', 'artwork_measurements_depth' : '', 'artwork_size_notes' : '', 'auction_measureunit' : '', 'artwork_condition_in' : '', 'artwork_provenance' : '', 'artwork_exhibited' : '', 'artwork_literature' : '', 'artwork_images1' : '', 'artwork_images2' : '', 'artwork_images3' : '', 'artwork_images4' : '', 'artwork_images5' : '', 'image1_name' : '', 'image2_name' : '', 'image3_name' : '', 'image4_name' : '', 'image5_name' : '', 'lot_origin_url' : ''}
        self.saleno = auctionnumber
        self.auctiondate = ""
        self.auctiontitle = ""
        self.auctionlocation = ""
        self.lastlotnumber = 0


    def _decodeGzippedContent(cls, encoded_content):
        response_stream = io.BytesIO(encoded_content)
        decoded_content = ""
        try:
            gzipper = gzip.GzipFile(fileobj=response_stream)
            decoded_content = gzipper.read()
        except: # Maybe this isn't gzipped content after all....
            decoded_content = encoded_content
        decoded_content = decoded_content.decode('utf-8', 'ignore')
        return(decoded_content)

    _decodeGzippedContent = classmethod(_decodeGzippedContent)


    def _getCookieFromResponse(cls, lastHttpResponse):
        cookies = ""
        responseCookies = lastHttpResponse.getheader("Set-Cookie")
        pathPattern = re.compile(r"Path=/;", re.IGNORECASE)
        domainPattern = re.compile(r"Domain=[^;,]+(;|,)", re.IGNORECASE)
        expiresPattern = re.compile(r"Expires=[^;]+;", re.IGNORECASE)
        maxagePattern = re.compile(r"Max-Age=[^;]+;", re.IGNORECASE)
        samesitePattern = re.compile(r"SameSite=[^;]+;", re.IGNORECASE)
        securePattern = re.compile(r"secure;?", re.IGNORECASE)
        httponlyPattern = re.compile(r"HttpOnly;?", re.IGNORECASE)
        if responseCookies and responseCookies.__len__() > 1:
            cookieParts = responseCookies.split("Path=/")
            for i in range(cookieParts.__len__()):
                cookieParts[i] = re.sub(domainPattern, "", cookieParts[i])
                cookieParts[i] = re.sub(expiresPattern, "", cookieParts[i])
                cookieParts[i] = re.sub(maxagePattern, "", cookieParts[i])
                cookieParts[i] = re.sub(samesitePattern, "", cookieParts[i])
                cookieParts[i] = re.sub(securePattern, "", cookieParts[i])
                cookieParts[i] = re.sub(pathPattern, "", cookieParts[i])
                cookieParts[i] = re.sub(httponlyPattern, "", cookieParts[i])
                cookieParts[i] = cookieParts[i].replace(",", "")
                cookieParts[i] = re.sub(re.compile("\s+", re.DOTALL), "", cookieParts[i])
                cookies += cookieParts[i]
        cookies = cookies.replace(";;", ";")
        return(cookies)

    _getCookieFromResponse = classmethod(_getCookieFromResponse)


    def getPageContent(self):
        return(self.pageResponse.read())

    def formatDate(cls, datestr):
        mondict = {'Janvier' : 'Jan', 'Février' : 'Feb', 'Mars' : 'Mar', 'Avril' : 'Apr', 'Mai' : 'May', 'Juin' : 'Jun', 'Juillet' : 'Jul', 'Août' : 'Aug', 'Septembre' : 'Sep', 'Octobre' : 'Oct', 'Novembre' : 'Nov', 'Décembre' : 'Dec'}
        datestrcomponents = datestr.split(" ")
        if not datestr:
            return ""
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


    def fractionToDecimalSize(self, sizestring):
        sizestringparts = sizestring.split("x")
        if sizestringparts.__len__() < 1:
            sizestringparts = sizestring.split("by")
        unitPattern = re.compile("(\s*(in)|(cm)\s*$)", re.IGNORECASE)
        ups = re.search(unitPattern, sizestringparts[-1])
        unit = ""
        if ups:
            upsg = ups.groups()
            unit = upsg[0]
        sizestringparts[-1] = unitPattern.sub("", sizestringparts[-1])
        decimalsizeparts = []
        beginspacePattern = re.compile("^\s+")
        endspacePattern = re.compile("\s+$")
        for szpart in sizestringparts:
            szpart = beginspacePattern.sub("", szpart)
            szpart = endspacePattern.sub("", szpart)
            d_szpart = unicodefraction_to_decimal(szpart)
            decimalsizeparts.append(d_szpart)
        decimalsize = " x ".join(decimalsizeparts)
        decimalsize += " " + unit
        return decimalsize


    def getLotsFromPage(self):
        pageContent = self.currentPageContent
        soup = BeautifulSoup(pageContent, features="html.parser")
        lotdivtags = soup.find_all("div", {'class' : 'content'})
        # Get the auction page and extract sale info from it.
        request = urllib.request.Request(self.auctionurl, headers=self.httpHeaders)
        try:
            response = self.opener.open(request)
            responsecontent = self.__class__._decodeGzippedContent(response.read())
        except:
            responsecontent = ""
        rsoup = BeautifulSoup(responsecontent, features="html.parser")
        contentdivtags = rsoup.find_all("div", {'class' : 'content'})
        if contentdivtags.__len__() > 0:
            divcontents = contentdivtags[0].renderContents().decode("utf-8")
            divcontents = divcontents.replace("\n", "").replace("\r", "")
            contentparts = divcontents.split("<span")
            if contentparts.__len__() > 0:
                self.auctiontitle = contentparts[0]
                self.auctiontitle = self.__class__.htmltagPattern.sub("", self.auctiontitle)
        redspantag = rsoup.find("span", {'class' : 'red'})
        if redspantag is not None:
            self.auctiondate = redspantag.renderContents().decode('utf-8')
            self.auctiondate = self.auctiondate.replace("\n", "").replace("\r", "")
        #print(lotdivtags.__len__())
        return lotdivtags
        

    def getDetailsPage(self, detailUrl):
        self.requestUrl = detailUrl
        self.pageRequest = urllib.request.Request(self.requestUrl, headers=self.httpHeaders)
        self.pageResponse = None
        self.postData = {}
        try:
            self.pageResponse = self.opener.open(self.pageRequest)
            headers = self.pageResponse.getheaders()
        except:
            print ("Couldn't fetch page due to limited connectivity. Please check your internet connection and try again. %s"%sys.exc_info()[1].__str__())
        self.currentPageContent = self.__class__._decodeGzippedContent(self.getPageContent())
        return self.currentPageContent


    def encryptFilename(self, filename):
        k = Fernet.generate_key()
        f = Fernet(k)
        encfilename = f.encrypt(filename.encode())
        return encfilename

    def renameImageFile(self, basepath, imagefilename, mappedImagename):
        oldfilename = basepath + "/" + imagefilename
        newfilename = basepath + "/" + mappedImagename
        try:
            os.rename(oldfilename, newfilename)
        except:
            pass


    def getImagenameFromUrl(self, imageUrl):
        urlparts = imageUrl.split("/")
        imagefilepart = urlparts[-1]
        imagefilenameparts = imagefilepart.split("?")
        imagefilename = imagefilenameparts[0]
        return imagefilename


    def parseDetailPage(self, detailsPage, artistname, artwork_name, auction_number, lot_number, imagepath, downloadimages):
        baseUrl = "https://www.bernaerts.eu"
        detailData = {}
        brPattern = re.compile("<br\s*\/?>")
        beginspacePattern = re.compile("^\s+")
        endspacePattern = re.compile("\s+$")
        literaturePattern = re.compile("Bibliografia", re.IGNORECASE|re.DOTALL)
        provenancePattern = re.compile("Provenienza", re.IGNORECASE|re.DOTALL)
        editionPattern = re.compile("(es\.\s+\d+\/\d+)", re.IGNORECASE|re.DOTALL)
        sizePattern1 = re.compile("([\d\sx\.,]+)\s+(cm)", re.DOTALL)
        sizePattern2 = re.compile("([\d\sx\.,]+)\s+(in)", re.DOTALL)
        mediumPattern = re.compile("(Paneel)|(mahonie)|(doek)", re.IGNORECASE|re.DOTALL)
        yearPattern = re.compile("(\d{4})")
        soup = BeautifulSoup(detailsPage, features="html.parser")
        descdivtags = soup.find_all("div", {'class' : 'contentitem'})
        #print(descdivtags)
        #exit()
        if descdivtags.__len__() == 0:
            descdivtags = soup.find_all("div", {'class' : descriptionPattern})
        if descdivtags.__len__() > 0:
            descdivcontents = descdivtags[0].renderContents().decode('utf-8')
            descdivcontents = self.__class__.htmltagPattern.sub("", descdivcontents)
            allptags = descdivtags[0].find_all("p")
            print(allptags)
            exit()
            allptags_1 = descdivtags[-1].find_all("p")
            print(allptags_1)
            for ptag_1 in allptags_1[-1]:
                    size_data_info=ptag_1.split("(")[-1]
                    zps1 = re.search(sizePattern1, size_data_info)
                    zps2 = re.search(sizePattern2, size_data_info)
                    if zps1:
                        detailData['artwork_size_notes'] = zps1.groups()[0] + " cm"
                        detailData['auction_measureunit'] = "cm"
           

            for ptag in allptags:
                pcontent = ptag.renderContents().decode('utf-8')
                pcontent = pcontent.replace("\n", "").replace("\r", "")
                pcontent = self.__class__.htmltagPattern.sub("", pcontent)

                plines = pcontent.split(".")
                for pline in plines:
                    mps = re.search(mediumPattern, pline)
                    if mps:
                        detailData['artwork_materials'] = pline
                zps1 = re.search(sizePattern1, pcontent)
                zps2 = re.search(sizePattern2, pcontent)
                if zps1:
                    detailData['artwork_size_notes'] = zps1.groups()[0] + " cm"
                    detailData['auction_measureunit'] = "cm"
                elif zps2:
                    detailData['artwork_size_notes'] = zps2.groups()[0] + " in"
                    detailData['auction_measureunit'] = "in"
            detailData['artwork_description'] = descdivcontents
            detailData['artwork_description'] = detailData['artwork_description'].replace("\n", " ").replace("\r", "")
            detailData['artwork_description'] = detailData['artwork_description'].replace('"', "'")
            detailData['artwork_description'] = beginspacePattern.sub("", detailData['artwork_description'])
        imgultag = soup.find("ul", {'id' : 'pikame'})
        if imgultag is not None:
            allimgtags = imgultag.find_all("img")
            imgctr = 1
            if allimgtags.__len__() > 0:
                imgtag = allimgtags[0]
                imageurl = baseUrl + imgtag['src']
                imagename1 = self.getImagenameFromUrl(imageurl)
                imagename1 = str(imagename1)
                imagename1 = imagename1.replace("b'", "").replace("'", "")
                auctiontitle = self.auctiontitle.replace(" ", "_")
                processedAuctionTitle = auctiontitle.replace(" ", "_")
                artistname = beginspacePattern.sub("", artistname)
                artistname = endspacePattern.sub("", artistname)
                lot_number = beginspacePattern.sub("", lot_number)
                lot_number = endspacePattern.sub("", lot_number)
                processedArtistName = artistname.replace(" ", "_")
                processedArtistName = unidecode.unidecode(processedArtistName)
                newname1 = auction_number + "__" + processedArtistName + "__" + lot_number + "_a"
                encryptedFilename = newname1
                imagepathparts = imageurl.split("/")
                defimageurl = "/".join(imagepathparts[:-2])
                encryptedFilename = str(encryptedFilename).replace("b'", "")
                encryptedFilename = str(encryptedFilename).replace("'", "")
                detailData['image1_name'] = str(encryptedFilename) + ".jpg"
                detailData['artwork_images1'] = imageurl
            imgctr = 2
            if allimgtags.__len__() > 1:
                imgurl2 = allimgtags[1]['src']
                altimage2parts = imgurl2.split("/")
                altimageurl = "/".join(altimage2parts[:-2])
                artistname = artistname.strip()
                artistname = beginspacePattern.sub("", artistname)
                artistname = endspacePattern.sub("", artistname)
                lot_number = beginspacePattern.sub("", lot_number)
                lot_number = endspacePattern.sub("", lot_number)
                processedArtistName = artistname.replace(" ", "_")
                processedArtistName = unidecode.unidecode(processedArtistName)
                lot_number = lot_number.strip()
                newname1 = auction_number + "__" + processedArtistName + "__" + lot_number + "_b"
                encryptedFilename = newname1
                encryptedFilename = str(encryptedFilename).replace("b'", "")
                encryptedFilename = str(encryptedFilename).replace("'", "")
                detailData['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
                detailData['artwork_images' + str(imgctr)] = imgurl2
                imgctr += 1
            if allimgtags.__len__() > 2:
                imgurl3 = allimgtags[2]['src']
                altimage3parts = imgurl3.split("/")
                altimageurl = "/".join(altimage3parts[:-2])
                detailData['image' + str(imgctr) + '_name'] = self.getImagenameFromUrl(imgurl3)
                artistname = beginspacePattern.sub("", artistname)
                artistname = endspacePattern.sub("", artistname)
                lot_number = beginspacePattern.sub("", lot_number)
                lot_number = endspacePattern.sub("", lot_number)
                processedArtistName = artistname.replace(" ", "_")
                processedArtistName = unidecode.unidecode(processedArtistName)
                newname1 = auction_number + "__" + processedArtistName + "__" + lot_number + "_c"
                encryptedFilename = newname1
                encryptedFilename = str(encryptedFilename).replace("b'", "")
                encryptedFilename = str(encryptedFilename).replace("'", "")
                detailData['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
                detailData['artwork_images' + str(imgctr)] = imgurl3
                imgctr += 1
            if allimgtags.__len__() > 3:
                imgurl4 = allimgtags[3]['src']
                altimage4parts = imgurl4.split("/")
                altimageurl = "/".join(altimage4parts[:-2])
                detailData['image' + str(imgctr) + '_name'] = self.getImagenameFromUrl(imgurl4)
                artistname = beginspacePattern.sub("", artistname)
                artistname = endspacePattern.sub("", artistname)
                lot_number = beginspacePattern.sub("", lot_number)
                lot_number = endspacePattern.sub("", lot_number)
                processedArtistName = artistname.replace(" ", "_")
                processedArtistName = unidecode.unidecode(processedArtistName)
                newname1 = auction_number + "__" + processedArtistName + "__" + lot_number + "_d"
                encryptedFilename = newname1
                encryptedFilename = str(encryptedFilename).replace("b'", "")
                encryptedFilename = str(encryptedFilename).replace("'", "")
                detailData['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
                detailData['artwork_images' + str(imgctr)] = imgurl4
                imgctr += 1
        return detailData


    def getImage(self, imageUrl, imagepath, downloadimages):
        imageUrlParts = imageUrl.split("/")
        imagefilename = imageUrlParts[-1]
        if downloadimages == "1":
            pageRequest = urllib.request.Request(imageUrl, headers=self.httpHeaders)
            pageResponse = None
            try:
                pageResponse = self.opener.open(pageRequest)
            except:
                print ("Error: %s"%sys.exc_info()[1].__str__())
            try:
                imageContent = pageResponse.read()
                ifp = open(imagepath + os.path.sep + imagefilename, "wb")
                ifp.write(imageContent)
                ifp.close()
            except:
                print("Error: %s"%sys.exc_info()[1].__str__())


    def getInfoFromLotsData(self, htmldivtags, imagepath, downloadimages):
        baseUrl = "https://www.bernaerts.eu"
        info = []
        endSpacePattern = re.compile("\s+$", re.DOTALL)
        soldpricePattern = re.compile("([\d\s\.,]+)\s+€")
        beginspacePattern = re.compile("^\s+")
        artistnamePattern1 = re.compile("([^\(]+)\s+\((\d{4})\-(\d{4})\)\s*\(?(.*)\)?$", re.DOTALL)
        artistnamePattern2 = re.compile("([^\(]+)\s+$", re.DOTALL)
        signaturePattern = re.compile("(Handtekeningdragend)|(Getekend)|(Signatuur)", re.IGNORECASE)
        materialPattern = re.compile("(Olie)", re.IGNORECASE)
        estimatePattern1 = re.compile("Schatting\:\s*\&([lg]{1})t;\s*€\s*(\d+)", re.IGNORECASE|re.DOTALL)
        estimatePattern2 = re.compile("Schatting\:\s*€\s*(\d+)\s*\-\s*(\d+)", re.IGNORECASE|re.DOTALL)
        soldpricePattern = re.compile("Hamerprijs\:\s*€\s*(\d+)")
        matcatdict_en = {}
        matcatdict_fr = {}
        with open("/Users/saiswarupsahu/freelanceprojectchetan/docs/fineart_materials.csv", newline='') as mapfile:
        #with open("/root/artwork/deploydirnew/docs/fineart_materials.csv", newline='') as mapfile:
            mapreader = csv.reader(mapfile, delimiter=",", quotechar='"')
            for maprow in mapreader:
                matcatdict_en[maprow[1]] = maprow[3]
                matcatdict_fr[maprow[2]] = maprow[3]
        mapfile.close()
        for htmldiv in htmldivtags:
            data = {}
            data['lot_num'], data['artist_name'], data['artist_birth'], data['artist_death'], data['artwork_name'], data['artwork_measurements_height'], data['artwork_measurements_width'], data['artwork_measurements_depth'], data['artwork_materials'], data['price_estimate_min'], data['price_estimate_max'], data['price_sold'], data['artwork_markings'] = "", "", "", "", "", "", "", "", "", "", "", "", ""
            data['auction_num'] = self.saleno
            data['auction_location'] = self.auctionlocation
            data['auction_name'] = self.auctiontitle
            self.auctiondate = endSpacePattern.sub("", self.auctiondate)
            self.auctiondate = beginspacePattern.sub("", self.auctiondate)
            data['auction_start_date'] = self.auctiondate
            data['auction_house_name'] = "Bernaerts"
            lotno = ""
            detailUrl = ""
            htmlContent = htmldiv.renderContents().decode('utf-8')
            s = BeautifulSoup(htmlContent, features="html.parser")
            lotnoh3tag = s.find("h3")
            if lotnoh3tag is not None:
                lotno = lotnoh3tag.renderContents().decode('utf-8')
                lotno = lotno.replace("Lot ", "")
                data['lot_num'] = lotno
                self.lastlotnumber = lotno
            else:
                continue # We can't process data without lot number.
            artistspantag = s.find("span", {'class' : 'bold'})
            if artistspantag is not None:
                artistspancontents = artistspantag.renderContents().decode('utf-8')
                anps1 = re.search(artistnamePattern1, artistspancontents)
                anps2 = re.search(artistnamePattern2, artistspancontents)
                if anps1:
                    data['artist_name'] = anps1.groups()[0]
                    data['artist_birth'] = anps1.groups()[1]
                    data['artist_death'] = anps1.groups()[2]
                    data['artist_nationality'] = anps1.groups()[3]
                elif anps2:
                    data['artist_name'] = anps2.groups()[0]
                    data['artist_birth'] = ""
                    data['artist_death'] = ""
                    data['artist_nationality'] = ""
                else:
                    data['artist_name'] = ""
                    data['artist_birth'] = ""
                    data['artist_death'] = ""
                    data['artist_nationality'] = ""
            allptags = s.find_all("p")
            if allptags.__len__() > 1:
                titleptag = allptags[1]
                titlecontents = titleptag.renderContents().decode('utf-8')
                allplines = re.split(re.compile("<br\s*\/>", re.IGNORECASE|re.DOTALL), titlecontents)
                data['artwork_name'] = allplines[0]
                data['artwork_name'] = data['artwork_name'].replace("\n", "").replace("\r", "")
                for pline in allplines:
                    pline = pline.replace("\n", "").replace("\r", "")
                    data['artwork_materials']=pline.split('.')[0]
                    print(data['artwork_materials'])
                    sps = re.search(signaturePattern, pline)
                    if sps:
                        data['artwork_markings'] = pline
            else:
                data['artwork_name'] = ""
                data['artwork_markings'] = ""
            for ptag in allptags:
                pline = ptag.renderContents().decode('utf-8')
                pline = pline.replace("\n", "").replace("\r", "")
                eps1 = re.search(estimatePattern1, pline)
                eps2 = re.search(estimatePattern2, pline)
                spps = re.search(soldpricePattern, pline)
                #print(pline)
                if eps1:
                    ltgt = eps1.groups()[0]
                    if ltgt == "l":
                        data['price_estimate_max'] = eps1.groups()[1]
                        data['price_estimate_min'] = ""
                    elif ltgt == "g":
                        data['price_estimate_min'] = eps1.groups()[1]
                        data['price_estimate_max'] = ""
                elif eps2:
                    data['price_estimate_min'] = eps2.groups()[0]
                    data['price_estimate_max'] = eps2.groups()[1]
                if spps:
                    data['price_sold'] = spps.groups()[0]
            if htmldiv.parent.parent.name == "a":
                anchortag = htmldiv.parent.parent
                detailUrl = "https://www.bernaerts.eu/" + anchortag['href']
                detailUrl = detailUrl.replace("\n", "").replace("\r", "")
                data['lot_origin_url'] = detailUrl
            else:
                detailUrl = ""
                data['lot_origin_url'] = detailUrl
            #print(data['lot_num'] + " ## " + data['artist_name'] + " ## " + data['artist_birth'] + " ## " + data['artist_death'] + " ## " + data['price_estimate_min'] + " ## " + data['price_estimate_max'] + " ## " + data['price_sold'] + " ## " + data['artwork_name'] + " ## " + data['artwork_markings'])
            print("Getting '%s'..."%data['lot_origin_url'])
            if detailUrl != "":
                detailsPageContent = self.getDetailsPage(detailUrl)
            else:
                detailsPageContent = ""
            #print(detailsPageContent)
            detailData = self.parseDetailPage(detailsPageContent, data['artist_name'], data['artwork_name'], self.saleno, lotno, imagepath, downloadimages)
            
            for k in detailData.keys():
                data[k] = detailData[k]
            if 'price_sold' not in data.keys() or data['price_sold'] == "":
                data['price_sold'] = ""
            alphabetPattern = re.compile("[a-zA-Z]{2,}")
            if 'artwork_size_notes' in data.keys():
                sizeparts = data['artwork_size_notes'].split("x")
                if sizeparts.__len__() > 0:
                    data['artwork_measurements_height'] = sizeparts[0]
                if sizeparts.__len__() > 1:
                    data['artwork_measurements_width'] = sizeparts[1]
                    data['artwork_measurements_width'] = alphabetPattern.sub("", data['artwork_measurements_width'])
                if sizeparts.__len__() > 2:
                    data['artwork_measurements_depth'] = sizeparts[2]
                    data['artwork_measurements_depth'] = alphabetPattern.sub("", data['artwork_measurements_depth'])
                if 'artwork_measurements_height' in data.keys():
                    data['artwork_measurements_height'] = data['artwork_measurements_height'].replace("\n", "").replace("\r", "")
                if 'artwork_measurements_width' in data.keys():
                    data['artwork_measurements_width'] = data['artwork_measurements_width'].replace("\n", "").replace("\r", "")
                if 'artwork_measurements_depth' in data.keys():
                    data['artwork_measurements_depth'] = data['artwork_measurements_depth'].replace("\n", "").replace("\r", "")
                data['artwork_size_notes'] = data['artwork_size_notes'].replace("\n", "").replace("\r", "")
            withdrawnPattern = re.compile("withdrawn", re.IGNORECASE|re.DOTALL)
            data['price_kind'] = "unknown"
            if re.search(withdrawnPattern, data['price_sold']) or re.search(withdrawnPattern, data['price_estimate_max']):
                data['price_kind'] = "withdrawn"
            elif 'price_sold' in data.keys() and data['price_sold'] != "":
                data['price_kind'] = "price realized"
            elif 'price_estimate_max' in data.keys() and data['price_estimate_max'] != "":
                data['price_kind'] = "estimate"
            else:
                pass
           
            if 'artwork_materials' in data.keys():
                materials = data['artwork_materials']
                materialparts = materials.split(" ")
                catfound = 0
                for matpart in materialparts:
                    if matpart in ['in', 'on', 'of', 'the', 'from']:
                        continue
                    try:
                        matPattern = re.compile(matpart, re.IGNORECASE|re.DOTALL)
                        for enkey in matcatdict_en.keys():
                            if re.search(matPattern, enkey):
                                data['artwork_category'] = matcatdict_en[enkey]
                                catfound = 1
                                break
                        for frkey in matcatdict_fr.keys():
                            if re.search(matPattern, frkey):
                                data['artwork_category'] = matcatdict_fr[frkey]
                                catfound = 1
                                break
                        if catfound:
                            break
                    except:
                        pass
            data['artwork_markings']=data['artwork_markings'].replace(data['artwork_materials'],"")
            info.append(data)
            
        return info


    def getNextPage(self, requestUrl):
        request = urllib.request.Request(requestUrl, headers=self.httpHeaders)
        pageResponse = None
        try:
            pageResponse = self.opener.open(request)
            pagecontent = self.__class__._decodeGzippedContent(pageResponse.read())
        except:
            print ("Error: %s"%sys.exc_info()[1].__str__())
            pagecontent = ""
        return pagecontent

"""
[
'auction_house_name', 'auction_location', 'auction_num', 'auction_start_date', 'auction_end_date', 'auction_name', 'lot_num', 'sublot_num', 'price_kind', 'price_estimate_min', 'price_estimate_max', 'price_sold', 'artist_name', 'artist_birth', 'artist_death', 'artist_nationality', 'artwork_name', 'artwork_year_identifier', 'artwork_start_year', 'artwork_end_year', 'artwork_materials', 'artwork_category', 'artwork_markings', 'artwork_edition', 'artwork_description', 'artwork_measurements_height', 'artwork_measurements_width', 'artwork_measurements_depth', 'artwork_size_notes', 'auction_measureunit', 'artwork_condition_in', 'artwork_provenance', 'artwork_exhibited', 'artwork_literature', 'artwork_images1', 'artwork_images2', 'artwork_images3', 'artwork_images4', 'artwork_images5', 'image1_name', 'image2_name', 'image3_name', 'image4_name', 'image5_name', 'lot_origin_url'
]
 """
 
# That's it.... 

def updatestatus(auctionno, auctionurl):
    auctionurl = auctionurl.replace("%3A", ":")
    auctionurl = auctionurl.replace("%2F", "/")
    pageurl = "http://216.137.189.57:8080/scrapers/finish/?scrapername=Bernaerts&auctionnumber=%s&auctionurl=%s&scrapertype=2"%(auctionno, urllib.parse.quote(auctionurl))
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
    bernaerts = BernaertsBot(auctionurl, auctionnumber)
    fp = open(csvpath, "w")
    fieldnames = ['auction_house_name', 'auction_location', 'auction_num', 'auction_start_date', 'auction_end_date', 'auction_name', 'lot_num', 'sublot_num', 'price_kind', 'price_estimate_min', 'price_estimate_max', 'price_sold', 'artist_name', 'artist_birth', 'artist_death', 'artist_nationality', 'artwork_name', 'artwork_year_identifier', 'artwork_start_year', 'artwork_end_year', 'artwork_materials', 'artwork_category', 'artwork_markings', 'artwork_edition', 'artwork_description', 'artwork_measurements_height', 'artwork_measurements_width', 'artwork_measurements_depth', 'artwork_size_notes', 'auction_measureunit', 'artwork_condition_in', 'artwork_provenance', 'artwork_exhibited', 'artwork_literature', 'artwork_images1', 'artwork_images2', 'artwork_images3', 'artwork_images4', 'artwork_images5', 'image1_name', 'image2_name', 'image3_name', 'image4_name', 'image5_name', 'lot_origin_url']
    fieldsstr = ",".join(fieldnames)
    fp.write(fieldsstr + "\n")
    while True:
        soup = BeautifulSoup(bernaerts.currentPageContent, features="html.parser")
        lotsdata = bernaerts.getLotsFromPage()
        if lotsdata.__len__() == 0:
            break
        info = bernaerts.getInfoFromLotsData(lotsdata, imagepath, downloadimages)
        lotctr = 0 
        for d in info:
            lotctr += 1
            for f in fieldnames:
                if f in d and d[f] is not None:
                    fp.write('"' + str(d[f]) + '",')
                else:
                    fp.write('"",')
            fp.write("\n")
        bernaerts.lastlotnumber = int(bernaerts.lastlotnumber) + 1
        requestUrl = "https://www.bernaerts.eu/tags/veiling_ajax.php?cookie=&cataloog=c1085&zitting=3&sql_sort_method=0&start_page=0&show_rows=150&sql_lot_range=&lijst=0&search_mode=&search_data=&verkocht=1"#%(bernaerts.catalognumber, str(bernaerts.lastlotnumber))
        bernaerts.currentPageContent = bernaerts.getNextPage(requestUrl)
    fp.close()
    updatestatus(auctionnumber, auctionurl)
#https://www.bernaerts.eu/tags/komende_ajax.php?cookie=&cataloog=c1088&zitting=7&sql_sort_method=0&start_page=0&show_rows=21&sql_lot_range=63&lijst=0&search_mode=&search_data=&verkocht=00
# Example: python bernaerts.py "https://www.bernaerts.eu/en/auctions/auction-results-grid/?veil=c1085&zitting=3&verkocht=1" c1085  /Users/saiswarupsahu/freelanceprojectchetan/bernaerts_c1085.csv  /Users/saiswarupsahu/freelanceprojectchetan/Aguttes/Image/121480   0  0 



# supmit

