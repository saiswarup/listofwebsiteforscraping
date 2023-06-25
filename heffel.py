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
from cryptography.fernet import Fernet
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


class HeffelBot(object):
    
    startUrl=r"https://www.heffel.com/auction-catalog/modern-art_OH64A0G02J?pageNum=1"
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
        self.httpHeaders = { 'User-Agent' : r'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36',  'Accept' : 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8', 'Accept-Language' : 'en-us,en;q=0.5', 'Accept-Encoding' : 'gzip,deflate', 'Accept-Charset' : 'ISO-8859-1,utf-8;q=0.7,*;q=0.7', 'Keep-Alive' : '115', 'Connection' : 'keep-alive', }
        self.httpHeaders['cache-control'] = "max-age=0"
        self.httpHeaders['upgrade-insecure-requests'] = "1"
        self.httpHeaders['sec-fetch-dest'] = "document"
        self.httpHeaders['sec-fetch-mode'] = "navigate"
        self.httpHeaders['sec-fetch-site'] = "same-origin"
        self.httpHeaders['sec-fetch-user'] = "?1"
        self.homeDir = os.getcwd()
        #self.requestUrl = self.__class__.startUrl
        self.requestUrl = auctionurl
        parsedUrl = urlparse(self.requestUrl)
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



    def _decodeGzippedContent(cls, encoded_content):
        response_stream = io.BytesIO(encoded_content)
        decoded_content = ""
        try:
            gzipper = gzip.GzipFile(fileobj=response_stream)
            decoded_content = gzipper.read()
        except: # Maybe this isn't gzipped content after all....
            decoded_content = encoded_content
        decoded_content = decoded_content.decode('utf-8')
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
        mondict = {'January' : '01', 'February' : '02', 'March' : '03', 'April' : '04', 'May' : '05', 'June' : '06', 'July' : '07', 'August' : '08', 'September' : '09', 'October' : '10', 'November' : '11', 'December' : '12' }
        mondict3 = {'jan.' : '01', 'fév.' : '02', 'mar.' : '03', 'avr.' : '04', 'mai.' : '05', 'jui.' : '06', 'jul.' : '07', 'aoû.' : '08', 'sep.' : '09', 'oct.' : '10', 'nov.' : '11', 'déc.' : '12' }
        mondict4 = {'Janvier' : '01', 'Février' : '02', 'Mars' : '03', 'Avril' : '04', 'Mai' : '05', 'Juin' : '06', 'Juillet' : '07', 'Août' : '08', 'Septembre' : '09', 'Octobre' : '10', 'Novembre' : '11', 'Décembre' : '12'}
        datestrcomponents = datestr.split(" ")
        if not datestr:
            return ""
        dd = datestrcomponents[1]
        mm = '01'
        datestrcomponents[0] = datestrcomponents[0].capitalize()
        if datestrcomponents[0] in mondict.keys():
            mm = mondict[datestrcomponents[0]]
        else:
            try:
                mm = mondict3[datestrcomponents[0]]
            except:
                mm = mondict4[datestrcomponents[0]]
        yyyy = datestrcomponents[2]
        yyyy = yyyy.replace(",", "")
        retdate = mm + "/" + dd + "/" + yyyy
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
        alldivtags = soup.find_all("div", {'id' : 'MainContent_AuctionInfo_divInfo'})
        if alldivtags.__len__() > 0:
            title = alldivtags[0].renderContents().decode('utf-8')
            titleparts = title.split("<br/>")
            title = titleparts[0]
            title = self.__class__.htmltagPattern.sub("", title)
            beginspacePattern = re.compile("^\s+")
            endspacePattern = re.compile("\s+$")
            title = beginspacePattern.sub("", title)
            title = endspacePattern.sub("", title)
            self.auctiontitle = title
            auctiondate = titleparts[-1]
            auctiondateparts = auctiondate.split("|")
            auctiondate = auctiondateparts[0]
            auctiondate = auctiondate.strip(" ")
            self.auctiondate = auctiondate
        lotblocks = soup.find_all("div", {'class' : 'height-adj-sm-2 tile-align-text'})
        return lotblocks
        

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


    def renameImagefile(self, basepath, imagefilename, mappedImagename):
        oldfilename = basepath + "/" + imagefilename
        newfilename = basepath + "/" + mappedImagename
        try:
            os.rename(oldfilename, newfilename)
        except:
            print(oldfilename)


    def getImagenameFromUrl(self, imageUrl):
        urlparts = imageUrl.split("/")
        imagefilepart = urlparts[-1]
        imagefilenameparts = imagefilepart.split("?")
        imagefilename = imagefilenameparts[0]
        return imagefilename


    def parseDetailPage(self, detailsPage, lotno, imagepath, artistname, artworkname, downloadimages):
        baseUrl = "https://www.heffel.com"
        detailData = {}
        soup = BeautifulSoup(detailsPage, features="html.parser")
        mediumPattern = re.compile("(gold)|(silver)|(brass)|(bronze)|(wood)|(porcelain)|(stone)|(marble)|(metal)|(steel)|(iron)|(glass)|(plexiglas)|(chromogenic)|(paper)|(canvas)|(masonite)|(newsprint)|(silkscreen)|(parchment)|(linen)|(inkjet)|(ink\s+jet)|(pigment)|(\stin\s)|(photogravure)|(^oil\s+)|(\s+panel\s+)|(terracotta)|(ivory)|(\s+oak\s+)|(^oak\s+)|(\s+oak$)|(alabaster)", re.DOTALL|re.IGNORECASE)
        nonenglishmediumPattern = re.compile("(crayon)|(encre)|(plume)|(plume\s+et\s+encre)|(papier)|(pastel)|(craie)|(gouachée)|(aquarelle)|(lithographique)|(plomb)|(huile)|(cuivre)|(toile)|(bronze)|(Plâtre)|(en\s+terre\s+de\s+faïence)", re.IGNORECASE|re.DOTALL)
        provenancePattern = re.compile("PROVENANCE", re.DOTALL)
        literaturePattern = re.compile("LITERATURE", re.DOTALL)
        yearfromPattern = re.compile("dated\s+(\d{4})\s+", re.IGNORECASE|re.DOTALL)
        beginspacePattern = re.compile("^\s+")
        artistdatestags = soup.find_all("span", {'id' : 'MainContent_artistDates'})
        if artistdatestags.__len__() > 0:
            artistdates = artistdatestags[0].renderContents().decode('utf-8')
            dateparts = artistdates.split("-")
            if dateparts.__len__() > 0:
                detailData['artist_birth'] = dateparts[0]
            if dateparts.__len__() > 1:
                detailData['artist_death'] = dateparts[1]
                detailData['artist_death'] = beginspacePattern.sub("", detailData['artist_death'])
        titletags = soup.find_all("span", {'id' : 'MainContent_itemTitle'})
        if titletags.__len__() > 0:
            itemtitle = titletags[0].renderContents().decode('utf-8')
            detailData['artwork_name'] = itemtitle
        signtags = soup.find_all("span", {'id' : 'MainContent_itemInscription'})
        if signtags.__len__() > 0:
            signcontents = signtags[0].renderContents().decode('utf-8')
            signcontents = signcontents.replace('"', "'")
            yfs = re.search(yearfromPattern, signcontents)
            if yfs:
                detailData['artwork_start_year'] = yfs.groups()[0]
            detailData['artwork_markings'] = signcontents
        allptags = soup.find_all("p", {'class' : 'text-light lot-details-font-md break-word'})
        for ptag in allptags:
            pcontents = ptag.renderContents().decode('utf-8')
            pcontents = self.__class__.htmltagPattern.sub(" ", pcontents)
            psm = re.search(provenancePattern, pcontents)
            lsm = re.search(literaturePattern, pcontents)
            if psm:
                pcontents = pcontents.replace('"', "'")
                detailData['artwork_provenance'] = pcontents
                detailData['artwork_provenance'] = provenancePattern.sub("", detailData['artwork_provenance'])
                detailData['artwork_provenance'] = beginspacePattern.sub("", detailData['artwork_provenance'])
            if lsm:
                pcontents = pcontents.replace('"', "'")
                detailData['artwork_literature'] = pcontents
                detailData['artwork_literature'] = literaturePattern.sub("", detailData['artwork_literature'])
                detailData['artwork_literature'] = beginspacePattern.sub("", detailData['artwork_literature'])
        imgtags = soup.find_all("img", {'id' : 'MainContent_bigImage'})
        defaultimageurl = ""
        if imgtags.__len__() > 0:
            defaultimageurl = baseUrl + imgtags[0]['src']
        imagename1 = self.getImagenameFromUrl(defaultimageurl)
        imagename1 = str(imagename1)
        imagename1 = imagename1.replace("b'", "").replace("'", "")
        auctiontitle = self.auctiontitle.replace(" ", "_")
        processedAuctionTitle = auctiontitle.replace(" ", "_")
        processedArtistName = artistname.replace(" ", "_")
        processedArtistName = unidecode.unidecode(processedArtistName)
        processedArtworkName = artworkname.replace(" ", "_")
        sublot_number = ""
        #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + self.saleno + "__" + lotno + "__" + sublot_number
        newname1 = self.saleno + "__" + processedArtistName + "__" + lotno + "_a"
        #encryptedFilename = self.encryptFilename(newname1)
        encryptedFilename = newname1
        imagepathparts = defaultimageurl.split("/")
        defimageurl = "/".join(imagepathparts[:-2])
        encryptedFilename = str(encryptedFilename).replace("b'", "")
        encryptedFilename = str(encryptedFilename).replace("'", "")
        detailData['image1_name'] = str(encryptedFilename) + ".jpg"
        detailData['artwork_images1'] = defaultimageurl
        containerdivtags = soup.find_all("div", {'class' : 'container1', 'align' : 'center'})
        altimages = []
        if containerdivtags.__len__() > 0:
            allanchortags = containerdivtags[0].find_all("a")
            for anchortag in allanchortags:
                anchorUrl = baseUrl + "/Auction/" + anchortag['href']
                try:
                    anchorpagecontent = requests.get(anchorUrl).text
                except:
                    continue
                anchorsoup = BeautifulSoup(anchorpagecontent, features="html.parser")
                anchorimgtags = anchorsoup.find_all("img", {'id' : 'MainContent_bigImage'})
                if anchorimgtags.__len__() > 0:
                    altimgurl = baseUrl + anchorimgtags[0]['src']
                    altimages.append(altimgurl)
        imgctr = 2
        if altimages.__len__() > 0:
            altimage2 = altimages[0]
            altimage2parts = altimage2.split("/")
            altimageurl = "/".join(altimage2parts[:-2])
            processedArtistName = artistname.replace(" ", "_")
            processedArtistName = unidecode.unidecode(processedArtistName)
            processedArtworkName = artworkname.replace(" ", "_")
            sublot_number = ""
            #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + self.saleno + "__" + lotno + "__" + sublot_number
            newname1 = self.saleno + "__" + processedArtistName + "__" + lotno + "_b"
            #encryptedFilename = self.encryptFilename(newname1)
            encryptedFilename = newname1
            detailData['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
            detailData['artwork_images' + str(imgctr)] = altimage2
            imgctr += 1
        if altimages.__len__() > 1:
            altimage2 = altimages[1]
            altimage2parts = altimage2.split("/")
            altimageurl = "/".join(altimage2parts[:-2])
            processedArtistName = artistname.replace(" ", "_")
            processedArtistName = unidecode.unidecode(processedArtistName)
            processedArtworkName = artworkname.replace(" ", "_")
            sublot_number = ""
            #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + self.saleno + "__" + lotno + "__" + sublot_number
            newname1 = self.saleno + "__" + processedArtistName + "__" + lotno + "_c"
            #encryptedFilename = self.encryptFilename(newname1)
            encryptedFilename = newname1
            detailData['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
            detailData['artwork_images' + str(imgctr)] = altimage2
            imgctr += 1
        if altimages.__len__() > 2:
            altimage2 = altimages[2]
            altimage2parts = altimage2.split("/")
            altimageurl = "/".join(altimage2parts[:-2])
            processedArtistName = artistname.replace(" ", "_")
            processedArtistName = unidecode.unidecode(processedArtistName)
            processedArtworkName = artworkname.replace(" ", "_")
            sublot_number = ""
            #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + self.saleno + "__" + lotno + "__" + sublot_number
            newname1 = self.saleno + "__" + processedArtistName + "__" + lotno + "_d"
            #encryptedFilename = self.encryptFilename(newname1)
            encryptedFilename = newname1
            detailData['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
            detailData['artwork_images' + str(imgctr)] = altimage2
            imgctr += 1
        if altimages.__len__() > 3:
            altimage2 = altimages[3]
            altimage2parts = altimage2.split("/")
            altimageurl = "/".join(altimage2parts[:-2])
            processedArtistName = artistname.replace(" ", "_")
            processedArtistName = unidecode.unidecode(processedArtistName)
            processedArtworkName = artworkname.replace(" ", "_")
            sublot_number = ""
            #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + self.saleno + "__" + lotno + "__" + sublot_number
            newname1 = self.saleno + "__" + processedArtistName + "__" + lotno + "_e"
            #encryptedFilename = self.encryptFilename(newname1)
            encryptedFilename = newname1
            detailData['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
            detailData['artwork_images' + str(imgctr)] = altimage2
        soldforspantags = soup.find_all("span", {'id' : 'MainContent_soldFor'})
        if soldforspantags.__len__() > 0:
            soldforcontent = soldforspantags[0].renderContents().decode('utf-8')
            soldforcontent = self.__class__.htmltagPattern.sub("", soldforcontent)
            soldforPattern = re.compile("Sold\s+for\:\s*\$([\d\.,\s]+)", re.IGNORECASE|re.DOTALL)
            sps = re.search(soldforPattern, soldforcontent)
            if sps:
                detailData['price_sold'] = sps.groups()[0]
        descdivtags = soup.find_all("div", {'id' : 'divDescription'})
        if descdivtags.__len__() > 0:
            desccontents = descdivtags[0].renderContents().decode('utf-8')
            desccontents = desccontents.replace("\n", " ").replace("\r", " ")
            desccontents = self.__class__.htmltagPattern.sub("", desccontents)
            detailData['artwork_description'] = desccontents
            detailData['artwork_description'] = detailData['artwork_description'].strip()
            detailData['artwork_description'] = self.__class__.htmltagPattern.sub("", detailData['artwork_description'])
            detailData['artwork_description'] = detailData['artwork_description'].replace("\n", " ")
            detailData['artwork_description'] = detailData['artwork_description'].replace("\r", " ")
            detailData['artwork_description'] = detailData['artwork_description'].replace('"', "'")
            detailData['artwork_description'] = detailData['artwork_description'].replace("PROVENANCE", "<br><strong>Provenance</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("LITERATURE", "<br><strong>Literature</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("EXHIBITED", "<br><strong>Exhibited</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("EXPOSITIONS", "<br><strong>Expositions</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("BIBLIOGRAPHIE", "<br><strong>Literature</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("Condition Report", "<br><strong>Condition Report</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("Notes:", "<br><strong>Notes:</strong><br>")
            detailData['artwork_description'] = "<strong><br>Description<br></strong>" + detailData['artwork_description']
        return detailData


    def getImage(self, imageUrl, imagepath, downloadimages):
        imageUrlParts = imageUrl.split("/")
        imagefilename = imageUrlParts[-2] + "_" + imageUrlParts[-1]
        imagedir = imageUrlParts[-2]
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
        return imagefilename


    def getInfoFromLotsData(self, htmlList, imagepath, downloadimages):
        baseUrl = "https://www.heffel.com"
        info = []
        endSpacePattern = re.compile("\s+$", re.DOTALL)
        soldpricePattern = re.compile("([\d\s\.,]+)\s+€")
        beginspacePattern = re.compile("^\s+")
        measureunitPattern = re.compile("([a-zA-Z]{2})")
        matcatdict_en = {}
        matcatdict_fr = {}
        #with open("docs/fineart_materials.csv", newline='') as mapfile:
        with open("/root/artwork/deploydirnew/docs/fineart_materials.csv", newline='') as mapfile:
            mapreader = csv.reader(mapfile, delimiter=",", quotechar='"')
            for maprow in mapreader:
                matcatdict_en[maprow[1]] = maprow[3]
                matcatdict_fr[maprow[2]] = maprow[3]
        mapfile.close()
        for htmldiv in htmlList:
            data = {}
            data['auction_num'] = self.saleno
            lotno = ""
            htmlContent = htmldiv.renderContents().decode('utf-8')
            s = BeautifulSoup(htmlContent, features="html.parser")
            infodivtags = s.find_all("div", {'class' : 'text col-md-10'})
            lotno = infodivtags[0].renderContents().decode('utf-8')
            lotno = lotno.replace("LOT", "")
            lotno = beginspacePattern.sub("", lotno)
            lotno = endSpacePattern.sub("", lotno)
            data['lot_num'] = lotno
            if not lotno:
                continue
            title, medium, size, estimate, artistname = "", "", "", "", ""
            if infodivtags.__len__() > 1:
                title = infodivtags[1].renderContents().decode('utf-8')
            if infodivtags.__len__() > 2:
                medium = infodivtags[2].renderContents().decode('utf-8')
            if infodivtags.__len__() > 3:
                size = infodivtags[3].renderContents().decode('utf-8')
                sizeparts = size.split(",")
                if sizeparts.__len__() > 0:
                    size = sizeparts[0]
            if infodivtags.__len__() > 4:
                estimate = infodivtags[4].renderContents().decode('utf-8')
                estimate = self.__class__.htmltagPattern.sub("", estimate)
                estimate = estimate.replace("$", "")
                estimate = estimate + " USD"
                estimate = estimate.replace("Estimate:", "")
                estimate = beginspacePattern.sub("", estimate)
            artistnamedivtags = s.find_all("div", {'class' : 'headings col-md-10'})
            if artistnamedivtags.__len__() > 0:
                artistname = artistnamedivtags[0].renderContents().decode('utf-8')
                artistname = beginspacePattern.sub("", artistname)
                artistname = endSpacePattern.sub("", artistname)
            data['artist_name'] = artistname
            data['artwork_name'] = title
            data['artwork_size_notes'] = size
            sizeparts = size.split("x")
            data['artwork_measurements_height'] = sizeparts[0]
            if sizeparts.__len__() > 1:
                data['artwork_measurements_width'] = sizeparts[1]
                mups = re.search(measureunitPattern, data['artwork_measurements_width'])
                if mups:
                    data['auction_measureunit'] = mups.groups()[0]
                    data['artwork_measurements_width'] = measureunitPattern.sub("", data['artwork_measurements_width'])
            if sizeparts.__len__() > 2:
                data['artwork_measurements_depth'] = sizeparts[2]
                mups = re.search(measureunitPattern, data['artwork_measurements_depth'])
                if mups:
                    data['auction_measureunit'] = mups.groups()[0]
                    data['artwork_measurements_depth'] = measureunitPattern.sub("", data['artwork_measurements_depth'])
            estimateparts = estimate.split(" - ")
            data['price_estimate_min'] = estimateparts[0]
            if estimateparts.__len__() > 1:
                data['price_estimate_max'] = estimateparts[1]
                data['price_estimate_max'] = data['price_estimate_max'].replace(" USD", "")
            data['artwork_materials'] = medium
            soldpricetags = s.find_all("div", {'class' : 'text col-md-12'})
            if soldpricetags.__len__() > 0:
                soldpricecontents = soldpricetags[0].renderContents().decode('utf-8')
                soldpricecontents = self.__class__.htmltagPattern.sub("", soldpricecontents)
                soldpricePattern = re.compile("([\d,\.]+)", re.DOTALL)
                sps = re.search(soldpricePattern, soldpricecontents)
                if sps:
                    data['price_sold'] = sps.groups()[0]
            data['auction_start_date'] = self.__class__.formatDate(self.auctiondate)
            data['auction_start_date'] = data['auction_start_date'].replace("\n", " ").replace("\r\n", " ").replace(",", "")
            data['auction_name'] = self.auctiontitle
            data['CATEGORY'] = '2d'
            sizeitems = size.split(",")
            if sizeitems.__len__() > 0:
                sizeparts = sizeitems[0].split("x")
                if sizeparts.__len__() != 2:
                    data['CATEGORY'] = '3d'
            detailUrl = ""
            previousdivtag = htmldiv.find_previous_sibling("div")
            if previousdivtag is not None:
                anchortags = previousdivtag.find_all("a")
                if anchortags.__len__() > 0:
                    detailUrl = baseUrl + "/Auction/" + anchortags[0]['href']
                    data['lot_origin_url'] = detailUrl
                    print("Getting '%s'..."%data['lot_origin_url'])
                    detailsPageContent = self.getDetailsPage(detailUrl)
                    if not lotno:
                        continue
                    detailData = self.parseDetailPage(detailsPageContent, lotno, imagepath, data['artist_name'], data['artwork_name'], downloadimages)
                    for k in detailData.keys():
                        data[k] = detailData[k]
            withdrawnPattern = re.compile("withdrawn", re.IGNORECASE|re.DOTALL)
            data['price_kind'] = "unknown"
            if ('price_sold' in data.keys() and re.search(withdrawnPattern, data['price_sold'])) or ('price_estimate_max' in data.keys() and re.search(withdrawnPattern, data['price_estimate_max'])):
                data['price_kind'] = "withdrawn"
            elif 'price_sold' in data.keys() and data['price_sold'] != "":
                data['price_kind'] = "price realized"
            elif 'price_estimate_max' in data.keys() and data['price_estimate_max'] != "":
                data['price_kind'] = "estimate"
            else:
                pass
            if 'price_sold' not in data.keys():
                data['price_sold'] = ""
            data['auction_house_name'] = "HEFFEL"
            if 'artwork_materials' in detailData.keys() and 'artwork_category' not in detailData.keys():
                materials = detailData['artwork_materials']
                materialparts = materials.split(" ")
                catfound = 0
                for matpart in materialparts:
                    if matpart in ['in', 'on', 'of', 'the', 'from']:
                        continue
                    try:
                        matPattern = re.compile(matpart, re.IGNORECASE|re.DOTALL)
                        for enkey in matcatdict_en.keys():
                            if re.search(matPattern, enkey):
                                detailData['artwork_category'] = matcatdict_en[enkey]
                                catfound = 1
                                break
                        for frkey in matcatdict_fr.keys():
                            if re.search(matPattern, frkey):
                                detailData['artwork_category'] = matcatdict_fr[frkey]
                                catfound = 1
                                break
                        if catfound:
                            break
                    except:
                        pass
            data['auction_location'] = "Vancouver"
            info.append(data)
        return info

"""
[
'auction_house_name', 'auction_location', 'auction_num', 'auction_start_date', 'auction_end_date', 'auction_name', 'lot_num', 'sublot_num', 'price_kind', 'price_estimate_min', 'price_estimate_max', 'price_sold', 'artist_name', 'artist_birth', 'artist_death', 'artist_nationality', 'artwork_name', 'artwork_year_identifier', 'artwork_start_year', 'artwork_end_year', 'artwork_materials', 'artwork_category', 'artwork_markings', 'artwork_edition', 'artwork_description', 'artwork_measurements_height', 'artwork_measurements_width', 'artwork_measurements_depth', 'artwork_size_notes', 'auction_measureunit', 'artwork_condition_in', 'artwork_provenance', 'artwork_exhibited', 'artwork_literature', 'artwork_images1', 'artwork_images2', 'artwork_images3', 'artwork_images4', 'artwork_images5', 'image1_name', 'image2_name', 'image3_name', 'image4_name', 'image5_name', 'lot_origin_url'
]
 """
 
# That's it.... 

def updatestatus(auctionno, auctionurl):
    auctionurl = auctionurl.replace("%3A", ":")
    auctionurl = auctionurl.replace("%2F", "/")
    pageurl = "http://216.137.189.57:8080/scrapers/finish/?scrapername=Heffel&auctionnumber=%s&auctionurl=%s&scrapertype=2"%(auctionno, urllib.parse.quote(auctionurl))
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
    heffel = HeffelBot(auctionurl, auctionnumber)
    fp = open(csvpath, "w")
    fieldnames = ['auction_house_name', 'auction_location', 'auction_num', 'auction_start_date', 'auction_end_date', 'auction_name', 'lot_num', 'sublot_num', 'price_kind', 'price_estimate_min', 'price_estimate_max', 'price_sold', 'artist_name', 'artist_birth', 'artist_death', 'artist_nationality', 'artwork_name', 'artwork_year_identifier', 'artwork_start_year', 'artwork_end_year', 'artwork_materials', 'artwork_category', 'artwork_markings', 'artwork_edition', 'artwork_description', 'artwork_measurements_height', 'artwork_measurements_width', 'artwork_measurements_depth', 'artwork_size_notes', 'auction_measureunit', 'artwork_condition_in', 'artwork_provenance', 'artwork_exhibited', 'artwork_literature', 'artwork_images1', 'artwork_images2', 'artwork_images3', 'artwork_images4', 'artwork_images5', 'image1_name', 'image2_name', 'image3_name', 'image4_name', 'image5_name', 'lot_origin_url']
    fieldsstr = ",".join(fieldnames)
    fp.write(fieldsstr + "\n")
    pagectr = 1
    while True:
        soup = BeautifulSoup(heffel.currentPageContent, features="html.parser")
        lotsdata = heffel.getLotsFromPage()
        info = heffel.getInfoFromLotsData(lotsdata, imagepath, downloadimages)
        lotctr = 0
        for d in info:
            lotctr += 1
            for f in fieldnames:
                if f in d and d[f] is not None:
                    fp.write('"' + str(d[f]) + '",')
                else:
                    fp.write('"",')
            fp.write("\n")
        pagectr += 1
        paginationdivtags = soup.find_all("div", {'class' : 'pagination'})
        if paginationdivtags.__len__() > 0:
            nextpageanchors = paginationdivtags[0].find_all("a")
            pageflag = True
            for pageanchor in nextpageanchors:
                anchorcontents = pageanchor.renderContents().decode("utf-8")
                if str(anchorcontents) == str(pagectr):
                    pageflag = False
                    nextpageUrl = heffel.baseUrl[:-1] + "/Auction/" + pageanchor['href']
                    print("Getting next page: %s"%nextpageUrl)
                    heffel.pageRequest = urllib.request.Request(nextpageUrl, headers=heffel.httpHeaders)
                    try:
                        heffel.pageResponse = heffel.opener.open(heffel.pageRequest)
                    except:
                        print("Couldn't find the page %s"%str(pagectr))
                        break
                    heffel.currentPageContent = heffel.__class__._decodeGzippedContent(heffel.getPageContent())
                    break
            if pageflag == True:
                break
    fp.close()
    updatestatus(auctionnumber, auctionurl)

# Example: python heffel.py "https://www.heffel.com/Auction/Lots_E?Request=iZTDNdl2DfJc8jRi4pFzNF4FyYcqe80krsL77dDV7HDrEQO27T3eHsu4f/jVY6k4Oh+BIvUaQIxS9iD0mQUROJTs2tIEI/isCF+TbellAu0uVT0rWjitl4E+ceHcN3zQ0Ir13YX+uwK9U+6TMdn2EjVqIfbucVaKQTC3S+V7zRUBNsix6Z/Gzpd9lJjWdYNbWqUwO3TDWHwellGCr+O/FVURQ1u7JeR/" 230721 /home/supmit/work/art2/heffel_230721.csv /home/supmit/work/art2/images/heffel/230721 0 0


# supmit

