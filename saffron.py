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


class SaffronBot(object):
    
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
        dd = datestrcomponents[0]
        mm = '01'
        datestrcomponents[1] = datestrcomponents[1].capitalize()
        if datestrcomponents[1] in mondict.keys():
            mm = mondict[datestrcomponents[1]]
        else:
            try:
                mm = mondict3[datestrcomponents[1]]
            except:
                mm = mondict4[datestrcomponents[1]]
        yyyy = datestrcomponents[2]
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
        titleclassPattern = re.compile("_title_")
        allh1tags = soup.find_all("h1", {'class' : titleclassPattern})
        titlePattern = re.compile("([\w\s]+)\s+\((.*)\)")
        if allh1tags.__len__() > 0:
            titlecontents = allh1tags[0].renderContents().decode('utf-8')
            beginspacePattern = re.compile("^\s+")
            endspacePattern = re.compile("\s+$")
            titlecontents = beginspacePattern.sub("", titlecontents)
            titlecontents = endspacePattern.sub("", titlecontents)
            titlecontents = titlecontents.replace("\n", "").replace("\r", "")
            titlecontents = self.__class__.htmltagPattern.sub("", titlecontents)
            tps = re.search(titlePattern, titlecontents)
            if tps:
                title = tps.groups()[0]
                date = tps.groups()[1]
                dateparts = date.split(" ")
                month = dateparts[1].lower()
                month = month[0].upper() + month[1:]
                date = dateparts[0] + " " + month + " " + dateparts[2]
                self.auctiontitle = title
                self.auctiondate = date
        lotblocks = soup.find_all("div", {'class' : 'rightpad'})
        print(lotblocks)
        exit()
        

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
        baseUrl = "https://www.saffronart.com"
        detailData = {}
        soup = BeautifulSoup(detailsPage, features="html.parser")
        estimatelabelPattern = re.compile("lblEstimates")
        #estimatePattern = re.compile("([\w\$]{1,2})\.?\s*([\d\.,\s\-]+)", re.DOTALL)
        estimatePattern = re.compile("(Rs)\.?\s*([\d\.,\s\-]+)", re.DOTALL)
        dollarnumberPattern = re.compile("\$(\d+)")
        yearPattern = re.compile("(\d{4})")
        workdetailsPattern = re.compile("_sn_Workdetails")
        provenancePattern = re.compile("__Provenance")
        publishPattern = re.compile("__PublishingDesc")
        editionPattern = re.compile("__TypeAndEditionDesc")
        imgtagPattern = re.compile("__Image")
        editionstrPattern = re.compile("edition", re.IGNORECASE)
        exhibitedPattern = re.compile("EXHIBITED")
        signedPattern = re.compile("signed", re.IGNORECASE)
        beginspacePattern = re.compile("^\s+")
        labeltags = soup.find_all("label", {'id' : estimatelabelPattern})
        if labeltags.__len__() > 0:
            labelcontents = labeltags[0].renderContents().decode('utf-8')
            eps = re.search(estimatePattern, labelcontents)
            if eps:
                currency = eps.groups()[0]
                estimaterange = eps.groups()[1]
                cps = re.search(dollarnumberPattern, currency)
                if cps:
                    currency = "$"
                    estimaterange = cps.groups()[0] + estimaterange
                suffix = " INR"
                if currency == "$":
                    suffix = " USD"
                elif currency == "Rs":
                    suffix = " INR"
                estimaterange = estimaterange.replace("\n", "").replace("\r", "")
                estimate = estimaterange + suffix
                estimateparts = estimate.split(" - ")
                detailData['price_estimate_min'] = estimateparts[0]
                if estimateparts.__len__() > 1:
                    detailData['price_estimate_max'] = estimateparts[1]
                    detailData['price_estimate_max'] = detailData['price_estimate_max'].replace(" INR", "").replace(" USD", "")
        detailspantags = soup.find_all("span", {'id' : workdetailsPattern})
        if detailspantags.__len__() > 0:
            detailscontent = detailspantags[0].parent.text
            detaillines = detailscontent.split("\n")
            for line in detaillines:
                sps = re.search(signedPattern, line)
                line = self.__class__.htmltagPattern.sub("", line)
                if sps:
                    detailData['artwork_markings'] = line
                    detailData['artwork_markings'] = detailData['artwork_markings'].replace('"', "'")
                    detailData['artwork_markings'] = self.__class__.htmltagPattern.sub("", detailData['artwork_markings'])
                    detailData['artwork_markings'] = detailData['artwork_markings'].replace("\n", "").replace("\r", "")
                    detailData['artwork_markings'] = beginspacePattern.sub("", detailData['artwork_markings'])
                yps = re.search(yearPattern, line)
                if yps:
                    detailData['artwork_start_year'] = yps.groups()[0]
                    detailData['artwork_start_year'] = self.__class__.htmltagPattern.sub("", detailData['artwork_start_year'])
                    detailData['artwork_start_year'] = detailData['artwork_start_year'].replace("\n", "").replace("\r", "")
                    detailData['artwork_start_year'] = beginspacePattern.sub("", detailData['artwork_start_year'])
        provenanceptags = soup.find_all("p", {'id' : provenancePattern})
        if provenanceptags.__len__() > 0:
            provenance = provenanceptags[0].renderContents().decode('utf-8')
            provenance = provenance.replace("\n", "").replace("\r", "")
            provenance = self.__class__.htmltagPattern.sub("", provenance)
            provenance = provenance.replace("PROVENANCE", "")
            detailData['artwork_provenance'] = provenance
        publisherptags = soup.find_all("p", {'id' : publishPattern})
        if publisherptags.__len__() > 0:
            publishercontents = publisherptags[0].renderContents().decode('utf-8')
            publishercontents = publishercontents.replace("\n", "").replace("\r", "")
            publishercontents = self.__class__.htmltagPattern.sub("", publishercontents)
            publishercontents = publishercontents.replace("PUBLISHED", "")
            if re.search(exhibitedPattern, publishercontents):
                detailData['artwork_exhibited'] = publishercontents
            else:
                detailData['artwork_literature'] = publishercontents
        editionptags = soup.find_all("p", {'id' : editionPattern})
        if editionptags.__len__() > 0:
            edition = editionptags[0].renderContents().decode('utf-8')
            edition = edition.replace("\n", "").replace("\r", "")
            edition = self.__class__.htmltagPattern.sub("", edition)
            if re.search(editionstrPattern, edition):
                detailData['artwork_edition'] = edition
                detailData['artwork_edition'] = beginspacePattern.sub("", detailData['artwork_edition'])
        allimgtags = soup.find_all("img", {'id' : imgtagPattern})
        defaultimageurl = ""
        if allimgtags.__len__() > 0:
            defaultimageurl = allimgtags[0]['src']
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
        detailsdivtags = soup.find_all("div", {'class' : 'artworkDetails'})
        detailData['artwork_description'] = ""
        if detailsdivtags.__len__() > 0:
            h3tags = detailsdivtags[0].find_all("h3")
            if h3tags.__len__() < 2:
                detailData['artwork_description'] = ""
                return detailData
            h3tag = h3tags[1]
            ptagslist = []
            ptag1 = h3tag.findNext("p")
            ptag2, ptag3, ptag4 = None, None, None
            if ptag1:
                ptagslist.append(ptag1)
                ptag2 = ptag1.findNext("p")
            if ptag2 is not None:
                ptagslist.append(ptag2)
                ptag3 = ptag2.findNext("p")
            if ptag3 is not None:
                ptagslist.append(ptag3)
                ptag4 = ptag3.findNext("p")
            if ptag4 is not None:
                ptagslist.append(ptag4)
            for ptag in ptagslist:
                try:
                    pcontent = ptag.renderContents().decode('utf-8')
                    pcontent = pcontent.replace("\n", "").replace("\r", "")
                    pcontent = self.__class__.htmltagPattern.sub("", pcontent)
                    detailData['artwork_description'] += " " + pcontent
                except:
                    pass
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
        baseUrl = "https://www.saffronart.com/auctions/"
        info = []
        endSpacePattern = re.compile("\s+$", re.DOTALL)
        soldpricePattern = re.compile("([\d\s\.,]+)\s+€")
        beginspacePattern = re.compile("^\s+")
        lotnoPattern = re.compile("Lot\s+(\d+)\s+\-\s+(.*)$")
        lotnoPattern2 = re.compile("Lot\s*(\d+)")
        arttitlePattern = re.compile("_ArtTitle_")
        mediumPattern = re.compile("_SurfaceMedium_")
        sizePattern1 = re.compile("_SizeInches_")
        sizePattern2 = re.compile("_SizeCms_")
        bdPattern1 = re.compile("\((\d{4})\s*\-\s*(\d{4})\)")
        measureunitPattern = re.compile("([a-zA-Z]{2})")
        matcatdict_en = {}
        matcatdict_fr = {}
        #with open("docs/fineart_materials.csv", newline='') as mapfile:
        with open("/Users/saiswarupsahu/freelanceprojectchetan/docs/fineart_materials.csv", newline='') as mapfile:
            mapreader = csv.reader(mapfile, delimiter=",", quotechar='"')
            for maprow in mapreader:
                matcatdict_en[maprow[1]] = maprow[3]
                matcatdict_fr[maprow[2]] = maprow[3]
        mapfile.close()
        for htmldiv in htmlList:
            data = {}
            data['auction_num'] = self.saleno
            lotno = ""
            artistname, title, medium, size, birthyear, deathyear = "", "", "", "", "", ""
            htmlContent = htmldiv.renderContents().decode('utf-8')
            s = BeautifulSoup(htmlContent, features="html.parser")
            allanchors = s.find_all("a", {'class' : 'morehyperlink'})
            print(allanchors)
            if allanchors.__len__() > 0:
                htmlanchor = allanchors[0]
                detailUrl = baseUrl + htmlanchor['href']
                artistname = htmlanchor.renderContents().decode('utf-8')
            else:
                detailUrl = ""
            data['lot_origin_url'] = detailUrl
            biddingwindowPattern = re.compile("BiddingWindow")
            biddingwindowdiv = htmldiv.findNext("div", {'id' : biddingwindowPattern})
            blockheaderdiv = htmldiv.findNext("div", {'class' : 'blockheader'})
            if biddingwindowdiv is not None:
                h4tags = biddingwindowdiv.find_all("h4")
                if h4tags.__len__() > 0:
                    h4contents = h4tags[0].renderContents().decode('utf-8')
                    h4contents = h4contents.replace("\n", "").replace("\r", "")
                    h4contents = self.__class__.htmltagPattern.sub("", h4contents)
                    lps = re.search(lotnoPattern, h4contents)
                    lps2 = re.search(lotnoPattern2, h4contents)
                    if lps:
                        lpsg = lps.groups()
                        lotno = lpsg[0]
                        artistname = lpsg[1]
                    elif lps2:
                        lpsg2 = lps2.groups()
                        lotno = lpsg2[0]
                        artistname = ""
                    else:
                        continue # if we do not get lotno, we can't go ahead 
                    #print(lotno + " ## " + artistname)
                else:
                    continue # if we do not get lotno, we can't go ahead 
            elif blockheaderdiv:
                blockcontent = blockheaderdiv.renderContents().decode('utf-8')
                lps2 = re.search(lotnoPattern2, blockcontent)
                if lps2:
                    lpsg2 = lps2.groups()
                    lotno = lpsg2[0]
                else:
                    continue
                #print(lotno + " ## " + artistname)
            artistname = artistname.replace(" USD payment only.", "")
            data['artist_name'] = artistname
            data['lot_num'] = lotno
            titlespantags = s.find_all("span", {'id' : arttitlePattern})
            if titlespantags.__len__() > 0:
                title = titlespantags[0].renderContents().decode('utf-8')
                title = title.replace("\n", "").replace("\r", "")
                title = self.__class__.htmltagPattern.sub("", title)
            mediumspantags = s.find_all("span", {'id' : mediumPattern})
            if mediumspantags.__len__() > 0:
                medium = mediumspantags[0].renderContents().decode('utf-8')
                medium = medium.replace("\n", "").replace("\r", "")
                medium = self.__class__.htmltagPattern.sub("", medium)
            sizespantags = s.find_all("span", {'id' : sizePattern1})
            if sizespantags.__len__() == 0:
                sizespantags = s.find_all("span", {'id' : sizePattern2})
            if sizespantags.__len__() > 0:
                size = sizespantags[0].renderContents().decode('utf-8')
                size = size.replace("\n", "").replace("\r", "")
                size = self.__class__.htmltagPattern.sub("", size)
            itemdetaildivtags = s.find_all("div", {'class' : 'itemdetail'})
            if itemdetaildivtags.__len__() > 0:
                childrendivtags = itemdetaildivtags[0].findChildren("div" , recursive=False)
                if childrendivtags.__len__() > 0:
                    firstchildcontents = childrendivtags[0].renderContents().decode('utf-8')
                    firstchildcontents = self.__class__.htmltagPattern.sub("", firstchildcontents)
                    firstchildcontents = firstchildcontents.replace("\n", "").replace("\r", "")
                    bdps1 = re.search(bdPattern1, firstchildcontents)
                    if bdps1:
                        birthyear = bdps1.groups()[0]
                        deathyear = bdps1.groups()[1]
            data['artwork_name'] = title
            data['artwork_materials'] = medium
            data['artwork_size_notes'] = size
            size = size.replace("by", "x")
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
            data['artist_birth'] = birthyear
            data['artist_death'] = deathyear
            soldpricedivtags = s.find_all("div", {'class' : 'winningbidamountdiv'})
            bidpattern = re.compile("[a-zA-Z\s]+")
            if soldpricedivtags.__len__() > 0:
                soldpricediv = soldpricedivtags[0]
                soldpricecontents = soldpricediv.renderContents().decode('utf-8')
                soldpricecontents = soldpricecontents.replace("\n", "").replace("\r", "")
                soldpriceparts = soldpricecontents.split("|")
                foundinr = 0
                soldprice = ""
                for soldprice in soldpriceparts:
                    if "Rs " in soldprice:
                        soldprice = soldprice.replace("Rs ", "")
                        soldprice = bidpattern.sub("", soldprice)
                        soldprice = soldprice + " INR"
                        soldprice = soldprice.replace("()", "")
                        soldprice = soldprice.replace("?", "")
                        soldprice = self.__class__.htmltagPattern.sub("", soldprice)
                        foundinr = 1
                        break
                    else:
                        continue
                if foundinr == 0:
                    soldprice = soldpriceparts[0]
                    if "$" in soldprice:
                        soldprice = soldprice.replace("$", "")
                        soldprice = bidpattern.sub("", soldprice)
                        soldprice = soldprice + " USD"
                    soldprice = self.__class__.htmltagPattern.sub("", soldprice)
                data['price_sold'] = soldprice
            """
            try:
                print(data['lot_num'] + " ## " + data['artist_name'] + " ## " + data['artist_birth'] + " ## " + data['artist_death'] + " ## " + data['artwork_materials'])
            except:
                print(data['lot_num'] + " ## " + data['artist_name'])
            """
            print("Getting '%s'..."%data['lot_origin_url'])
            if detailUrl != "":
                detailsPageContent = self.getDetailsPage(detailUrl)
                detailData = self.parseDetailPage(detailsPageContent, lotno, imagepath, data['artist_name'], data['artwork_name'], downloadimages)
            else:
                detailData = {}
            for k in detailData.keys():
                data[k] = detailData[k]
            if 'price_sold' not in data.keys() or data['price_sold'] == "":
                data['price_sold'] = ""
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
            data['auction_start_date'] = self.__class__.formatDate(self.auctiondate)
            data['auction_start_date'] = data['auction_start_date'].replace("\n", " ").replace("\r\n", " ")
            data['auction_name'] = self.auctiontitle
            data['auction_house_name'] = "SAFFRON"
            data['auction_location'] = "Mumbai"
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
    pageurl = "http://216.137.189.57:8080/scrapers/finish/?scrapername=Saffron&auctionnumber=%s&auctionurl=%s&scrapertype=2"%(auctionno, urllib.parse.quote(auctionurl))
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
    saffron = SaffronBot(auctionurl, auctionnumber)
    fp = open(csvpath, "w")
    fieldnames = ['auction_house_name', 'auction_location', 'auction_num', 'auction_start_date', 'auction_end_date', 'auction_name', 'lot_num', 'sublot_num', 'price_kind', 'price_estimate_min', 'price_estimate_max', 'price_sold', 'artist_name', 'artist_birth', 'artist_death', 'artist_nationality', 'artwork_name', 'artwork_year_identifier', 'artwork_start_year', 'artwork_end_year', 'artwork_materials', 'artwork_category', 'artwork_markings', 'artwork_edition', 'artwork_description', 'artwork_measurements_height', 'artwork_measurements_width', 'artwork_measurements_depth', 'artwork_size_notes', 'auction_measureunit', 'artwork_condition_in', 'artwork_provenance', 'artwork_exhibited', 'artwork_literature', 'artwork_images1', 'artwork_images2', 'artwork_images3', 'artwork_images4', 'artwork_images5', 'image1_name', 'image2_name', 'image3_name', 'image4_name', 'image5_name', 'lot_origin_url']
    fieldsstr = ",".join(fieldnames)
    fp.write(fieldsstr + "\n")
    pagectr = 1
    pagePattern = re.compile("PaginationDiv")
    pagenoPattern = re.compile("PageIndex=(\d+)")
    while True:
        soup = BeautifulSoup(saffron.currentPageContent, features="html.parser")
        lotsdata = saffron.getLotsFromPage()
        info = saffron.getInfoFromLotsData(lotsdata, imagepath, downloadimages)
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
        pagedivtags = soup.find_all("div", {'id' : pagePattern})
        nextpagefound = False
        if pagedivtags.__len__() > 0:
            pageanchortags = pagedivtags[0].find_all("a")
            for pageanchor in pageanchortags:
                if 'href' not in pageanchor.attrs.keys():
                    continue
                anchorurl = pageanchor['href']
                aps = re.search(pagenoPattern, anchorurl)
                if aps:
                    pageno = aps.groups()[0]
                    if int(pageno) == pagectr:
                        nextpageUrl = saffron.baseUrl + "auctions/" + anchorurl
                        nextpagefound = True
        if not nextpagefound:
            break
        print("Fetching next page: %s\n"%nextpageUrl)
        saffron.pageRequest = urllib.request.Request(nextpageUrl, headers=saffron.httpHeaders)
        try:
            saffron.pageResponse = saffron.opener.open(saffron.pageRequest)
        except:
            print("Couldn't find the page %s: Error: %s"%(str(pagectr), sys.exc_info()[1].__str__()))
            break
        saffron.currentPageContent = saffron.__class__._decodeGzippedContent(saffron.getPageContent())
    fp.close()
    updatestatus(auctionnumber, auctionurl)

# Example: python saffron.py https://www.saffronart.com/auctions/AuctionResults.aspx?eid=4154  4154 /Users/saiswarupsahu/freelanceprojectchetan/saffron_4154.csv /Users/saiswarupsahu/freelanceprojectchetan/ 0 0


