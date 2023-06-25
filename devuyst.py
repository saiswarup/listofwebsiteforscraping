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


class DevuystBot(object):
    
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
        self.httpHeaders = { 'User-Agent' : r'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36',  'Accept' : '*/*', 'Accept-Language' : 'en-us,en;q=0.5', 'Accept-Encoding' : 'gzip,deflate', 'Accept-Charset' : 'ISO-8859-1,utf-8;q=0.7,*;q=0.7', 'Connection' : 'keep-alive', }
        self.httpHeaders['Cache-Control'] = "no-cache"
        self.httpHeaders['Pragma'] = "no-cache"
        self.httpHeaders['upgrade-insecure-requests'] = "1"
        self.httpHeaders['Sec-Fetch-Dest'] = "empty"
        self.httpHeaders['Sec-Fetch-Mode'] = "cors"
        self.httpHeaders['Sec-Fetch-Site'] = "cross-site"
        self.httpHeaders['Origin'] = "https://de-vuyst.com/"
        self.httpHeaders['Referer'] = "https://de-vuyst.com/"
        self.homeDir = os.getcwd()
        self.requestUrl = "https://2wtahvb925-2.algolianet.com/1/indexes/*/queries?x-algolia-agent=Algolia%20for%20JavaScript%20(4.11.0);%20Browser%20(lite);%20instantsearch.js%20(4.36.0);%20Vue%20(2.6.14);%20Vue%20InstantSearch%20(4.3.0);%20JS%20Helper%20(3.7.0)&x-algolia-api-key=960d7b516f29234212f74ba49b50b6c3&x-algolia-application-id=2WTAHVB925"
        parsedUrl = urlparse(self.requestUrl)
        self.baseUrl = parsedUrl.scheme + "://" + parsedUrl.netloc + "/"
        #print(self.requestUrl)
        self.pageResponse = None
        self.requestMethod = "POST"
        data = '{"requests" : [{"indexName":"global_search","params":"filters=en:1&query=&facets=[]&tagFilters="}]}'.encode('utf-8')
        #self.postData = urllib.parse.urlencode(data)
        #print(self.postData)
        self.httpHeaders['Content-Length'] = data.__len__()
        self.pageRequest = urllib.request.Request(self.requestUrl, data=data, headers=self.httpHeaders)
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
        #print(self.currentPageContent)
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
        allh2tags = soup.find_all("h2", {'class' : 'main-subtitle'})
        if allh2tags.__len__() > 0:
            title = allh2tags[0].renderContents().decode('utf-8')
            title = title.replace("\n", "").replace("\r", "")
            beginspacePattern = re.compile("^\s+")
            endspacePattern = re.compile("\s+$")
            title = beginspacePattern.sub("", title)
            title = endspacePattern.sub("", title)
            self.auctiontitle = title
        allh1tags = soup.find_all("h1", {'class' : 'main-title'})
        if allh1tags.__len__() > 0:
            datetext = allh1tags[0].renderContents().decode('utf-8')
            datetext = datetext.replace("\n", "").replace("\r", "")
            datePattern = re.compile("(\d{1,2})\s+(\w+)\s+(\d{4})")
            dps = re.search(datePattern, datetext)
            if dps:
                dd = dps.groups()[0]
                month = dps.groups()[1]
                yyyy = dps.groups()[2]
                self.auctiondate = dd + " " + month + " " + yyyy
        #ulclassPattern = re.compile("views\-list\s+js\-views\-list")
        #rowultags = soup.find_all("ul", {'class' : ulclassPattern})
        #if rowultags.__len__() > 0:
        #    lotblocks = rowultags[0].find_all("li")
        jsondata = json.loads(pageContent)
        try:
            lotblocks = jsondata['results'][0]['hits']
        except:
            lotblocks = []
        #print(lotblocks)
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
        baseUrl = "https://de-vuyst.com"
        detailData = {}
        soup = BeautifulSoup(detailsPage, features="html.parser")
        divimageclassPattern = re.compile("slideshow\-print\-image")
        divimagetags = soup.find_all("div", {'class' : divimageclassPattern})
        defaultimageurl = ""
        if divimagetags.__len__() > 0:
            imgtags = divimagetags[0].find_all("img")
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


    def getInfoFromLotsData(self, datalist, imagepath, downloadimages):
        baseUrl = "https://de-vuyst.com"
        info = []
        endspacePattern = re.compile("\s+$", re.DOTALL)
        lotnoPattern = re.compile("Lot\s*(\d+)")
        priceclassPattern = re.compile("views\-item__price")
        materialclassPattern = re.compile("views\-item__material")
        detailsclassPattern = re.compile("views\-item__details")
        sizePattern1 = re.compile("([\d\.,]+\s+x\s+[\d\.,]+\s+x\s+[\d\.,]+\s*\w{2})")
        sizePattern2 = re.compile("([\d\.,]+\s+x\s+[\d\.,]+\s*\w{2})")
        signedPattern1 = re.compile("(signed\s+[^\-]+)\s*\-", re.IGNORECASE|re.DOTALL)
        signedPattern2 = re.compile("(sig\.\s+[^\-]+)\s*\-", re.IGNORECASE|re.DOTALL)
        signedPattern3 = re.compile("(Initials\s+[^\-]+)\s*\-", re.IGNORECASE|re.DOTALL)
        bdPattern = re.compile("(\d{4})\s+\-\s+(\d{4})")
        beginspacePattern = re.compile("^\s+")
        hyphenendPattern = re.compile("\s+\-\s*$")
        euroPattern = re.compile("€")
        usdPattern = re.compile("\$")
        literaturePattern = re.compile("literature", re.IGNORECASE|re.DOTALL)
        provenancePattern = re.compile("provenance", re.IGNORECASE|re.DOTALL)
        exhibitionPattern = re.compile("exhibition", re.IGNORECASE|re.DOTALL)
        nonmediumPattern = re.compile("(monogram)|(initial)|(inscription)|(label)|(sig\.)|(dedication)|(edition)|(frame)|(stamp)|(reverse)", re.IGNORECASE|re.DOTALL)
        emptyspacePattern = re.compile("^\s*$")
        singlealphaPattern = re.compile("\-[A-Z]{1}")
        absurlPattern = re.compile("^https?:\/\/")
        measureunitPattern = re.compile("([a-zA-Z]{2})")
        matcatdict_en = {}
        matcatdict_fr = {}
        with open("/Users/saiswarupsahu/freelanceprojectchetan/docs/fineart_materials.csv", newline='') as mapfile:
        #with open("/root/artwork/deploydirnew/docs/fineart_materials.csv", newline='') as mapfile:
            mapreader = csv.reader(mapfile, delimiter=",", quotechar='"')
            for maprow in mapreader:
                matcatdict_en[maprow[1]] = maprow[3]
                matcatdict_fr[maprow[2]] = maprow[3]
        mapfile.close()
        for datablock in datalist:
            data = {}
            data['auction_num'] = self.saleno
            lotno = ""
            print(datablock['title'])
            
            htmlContent = htmlli.renderContents().decode('utf-8')
            s = BeautifulSoup(htmlContent, features="html.parser")
            allanchors = s.find_all("a")
            htmlanchor = allanchors[0]
            if not re.search(absurlPattern, htmlanchor['href']):
                detailUrl = baseUrl + htmlanchor['href']
            else:
                detailUrl = htmlanchor['href']
            data['lot_origin_url'] = detailUrl
            birthyear, deathyear, artistname, title, estimate, medium, size, bdcontents = "", "", "", "", "", "", "", ""
            bdspantags = s.find_all("span", {'class' : 'views-item__author__country'})
            if bdspantags.__len__() > 0:
                bdcontents = bdspantags[0].renderContents().decode('utf-8')
                bdcontents = bdcontents.replace("\n", "").replace("\r", "")
                bdps = re.search(bdPattern, bdcontents)
                if bdps:
                    birthyear = bdps.groups()[0]
                    deathyear = bdps.groups()[1]
                    data['artist_birth'] = birthyear
                    data['artist_death'] = deathyear
                else:
                    birthyear = bdcontents
                    data['artist_birth'] = birthyear
                    data['artist_death'] = ""
                data['artist_birth'] = beginspacePattern.sub("", data['artist_birth'])
                data['artist_birth'] = endspacePattern.sub("", data['artist_birth'])
            artisth7tags = s.find_all("h7")
            if artisth7tags.__len__() > 0:
                artistcontents = artisth7tags[0].renderContents().decode('utf-8')
                artistcontents = self.__class__.htmltagPattern.sub("", artistcontents)
                artistcontents = artistcontents.replace("\n", "").replace("\r", "")
                artistcontents = artistcontents.replace(bdcontents, "")
                artistcontents = beginspacePattern.sub("", artistcontents)
                artistcontents = endspacePattern.sub("", artistcontents)
                artistname = artistcontents
                data['artist_name'] = artistname
                data['artist_name'] = data['artist_name'].replace('"', "'")
            titleh6tags = s.find_all("h6")
            if titleh6tags.__len__() > 0:
                titlecontents = titleh6tags[0].renderContents().decode('utf-8')
                titlecontents = titlecontents.replace("\n", "").replace("\r", "")
                title = titlecontents
                title = beginspacePattern.sub("", title)
                title = endspacePattern.sub("", title)
                data['artwork_name'] = title
                data['artwork_name'] = data['artwork_name'].replace('"', "'")
            lotnospantags = s.find_all("span", {'class' : 'views-item__lot'})
            if lotnospantags.__len__() > 0:
                lotnocontents = lotnospantags[0].renderContents().decode('utf-8')
                lotnocontents = self.__class__.htmltagPattern.sub("", lotnocontents)
                lotnocontents = lotnocontents.replace("\n", "").replace("\r", "")
                lps = re.search(lotnoPattern, lotnocontents)
                if lps:
                    lotno = lps.groups()[0]
                    data['lot_num'] = lotno
                else:
                    continue # No lot no, no processing
            else:
                continue
            estimatedivtags = s.find_all("div", {'class' : priceclassPattern})
            if estimatedivtags.__len__() > 0:
                estimatecontents = estimatedivtags[0].renderContents().decode('utf-8')
                estimatecontents = self.__class__.htmltagPattern.sub("", estimatecontents)
                estimatecontents = estimatecontents.replace("\n", "").replace("\r", "")
                estimate = lotnoPattern.sub("", estimatecontents)
                estimate = endspacePattern.sub("", estimate)
                eps = re.search(euroPattern, estimate)
                ups = re.search(usdPattern, estimate)
                if eps:
                    estimate = estimate + " EUR"
                    estimate = euroPattern.sub("", estimate)
                elif ups:
                    estimate = estimate + " USD"
                    estimate = usdPattern.sub("", estimate)
                estimate = singlealphaPattern.sub("", estimate)
                estimate = beginspacePattern.sub("", estimate)
                estimateparts = estimate.split(" - ")
                data['price_estimate_min'] = estimateparts[0]
                if estimateparts.__len__() > 1:
                    estimateparts[1] = estimateparts[1].replace(" USD", "").replace(" EUR", "")
                    data['price_estimate_max'] = estimateparts[1]
            mediumdivtags = s.find_all("div", {'class' : materialclassPattern})
            if mediumdivtags.__len__() > 0:
                mediumcontents = mediumdivtags[0].renderContents().decode('utf-8')
                mediumcontents = self.__class__.htmltagPattern.sub("", mediumcontents)
                mediumcontents = mediumcontents.replace("\n", "").replace("\r", "")
                zps1 = re.search(sizePattern1, mediumcontents)
                zps2 = re.search(sizePattern2, mediumcontents)
                if zps1 and 'artwork_size_notes' not in data.keys():
                    size = zps1.groups()[0]
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
                    medium = sizePattern1.sub("", mediumcontents)
                elif zps2 and 'artwork_size_notes' not in data.keys():
                    size = zps2.groups()[0]
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
                    medium = sizePattern2.sub("", mediumcontents)
                else:
                    data['artwork_size_notes'] = ""
                    medium = mediumcontents
                data['artwork_size_notes'] = data['artwork_size_notes'].replace('"', "'")
                sps1 = re.search(signedPattern1, medium)
                sps2 = re.search(signedPattern2, medium)
                sps3 = re.search(signedPattern3, medium)
                if sps1:
                    signature = sps1.groups()[0]
                    data['artwork_markings'] = signature
                elif sps2:
                    signature = sps2.groups()[0]
                    data['artwork_markings'] = signature
                elif sps3:
                    signature = sps3.groups()[0]
                    data['artwork_markings'] = signature
                else:
                    data['artwork_markings'] = ""
                data['artwork_markings'] = data['artwork_markings'].replace('"', "'")
                medium = signedPattern1.sub("", medium)
                medium = signedPattern2.sub("", medium)
                data['artwork_size_notes'] = beginspacePattern.sub("", data['artwork_size_notes'])
                medium = hyphenendPattern.sub("", medium)
                medium = beginspacePattern.sub("", medium)
                medium = endspacePattern.sub("", medium)
                medium = medium.replace('"', "'")
                mediumparts = medium.split("-")
                selectedmedium = []
                for mpart in mediumparts:
                    if re.search(nonmediumPattern, mpart) or re.search(emptyspacePattern, mpart):
                        continue
                    selectedmedium.append(mpart)
                medium = " - ".join(selectedmedium)
                data['artwork_materials'] = medium
            detailsdivtags = s.find_all("div", {'class' : detailsclassPattern})
            if detailsdivtags.__len__() > 0:
                detailscontents = detailsdivtags[0].renderContents().decode('utf-8')
                detailscontents = self.__class__.htmltagPattern.sub("", detailscontents)
                detailscontents = detailscontents.replace("\n", "").replace("\r", "")
                detailscontents = detailscontents.replace('"', "'")
                if re.search(literaturePattern, detailscontents):
                    data['artwork_literature'] = detailscontents
                else:
                    data['artwork_literature'] = ""
                data['artwork_provenance'] = ""
                if re.search(provenancePattern, detailscontents):
                    detailsparts = detailscontents.split("Provenance")
                    if detailsparts.__len__() > 1:
                        data['artwork_literature'] = detailsparts[0]
                        data['artwork_provenance'] = detailsparts[1]
                    elif detailsparts.__len__() > 0:
                        data['artwork_provenance'] = detailsparts[0]
                        data['artwork_literature'] = ""
                data['artwork_literature'] = literaturePattern.sub("", data['artwork_literature'])
                data['artwork_literature'] = beginspacePattern.sub("", data['artwork_literature'])
                data['artwork_provenance'] = beginspacePattern.sub("", data['artwork_provenance'])
                if re.search(exhibitionPattern, data['artwork_literature']):
                    data['artwork_exhibited'] = data['artwork_literature']
                    data['artwork_literature'] = ""
                    data['artwork_exhibited'] = exhibitionPattern.sub("", data['artwork_exhibited'])
                    data['artwork_exhibited'] = beginspacePattern.sub("", data['artwork_exhibited'])
            """
            data['auction_house_name'] = "DE VUYST"
            #print(data['lot_num'] + " ## " + data['artist_name'] + " ## " + data['artwork_name'] + " ## " + data['artwork_materials'] + " ## " + data['price_estimate_min'])
            """
            print("Getting '%s'..."%data['lot_origin_url'])
            detailsPageContent = self.getDetailsPage(detailUrl)
            if not lotno:
                continue
            detailData = self.parseDetailPage(detailsPageContent, lotno, imagepath, artistname, title, downloadimages)
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
            data['auction_start_date'] = self.__class__.formatDate(self.auctiondate)
            data['auction_start_date'] = data['auction_start_date'].replace("\n", " ").replace("\r\n", " ")
            data['auction_name'] = self.auctiontitle
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
            data['auction_location'] = "Belgium"
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
    pageurl = "http://216.137.189.57:8080/scrapers/finish/?scrapername=Devuyst&auctionnumber=%s&auctionurl=%s&scrapertype=2"%(auctionno, urllib.parse.quote(auctionurl))
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
    devuyst = DevuystBot(auctionurl, auctionnumber)
    fp = open(csvpath, "w")
    fieldnames = ['auction_house_name', 'auction_location', 'auction_num', 'auction_start_date', 'auction_end_date', 'auction_name', 'lot_num', 'sublot_num', 'price_kind', 'price_estimate_min', 'price_estimate_max', 'price_sold', 'artist_name', 'artist_birth', 'artist_death', 'artist_nationality', 'artwork_name', 'artwork_year_identifier', 'artwork_start_year', 'artwork_end_year', 'artwork_materials', 'artwork_category', 'artwork_markings', 'artwork_edition', 'artwork_description', 'artwork_measurements_height', 'artwork_measurements_width', 'artwork_measurements_depth', 'artwork_size_notes', 'auction_measureunit', 'artwork_condition_in', 'artwork_provenance', 'artwork_exhibited', 'artwork_literature', 'artwork_images1', 'artwork_images2', 'artwork_images3', 'artwork_images4', 'artwork_images5', 'image1_name', 'image2_name', 'image3_name', 'image4_name', 'image5_name', 'lot_origin_url']
    fieldsstr = ",".join(fieldnames)
    fp.write(fieldsstr + "\n")
    pagectr = 1
    while True:
        soup = BeautifulSoup(devuyst.currentPageContent, features="html.parser")
        lotsdata = devuyst.getLotsFromPage()
        if lotsdata.__len__() == 0:
            break
        info = devuyst.getInfoFromLotsData(lotsdata, imagepath, downloadimages)
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
        nextpageUrl = auctionurl + "?page=%s"%str(pagectr)
        devuyst.pageRequest = urllib.request.Request(nextpageUrl, headers=devuyst.httpHeaders)
        try:
            devuyst.pageResponse = devuyst.opener.open(devuyst.pageRequest)
        except:
            print("Couldn't find the page %s"%str(pagectr))
            break
        devuyst.currentPageContent = devuyst.__class__._decodeGzippedContent(devuyst.getPageContent())
    fp.close()
    updatestatus(auctionnumber, auctionurl)

# Example: python devuyst.py https://de-vuyst.com/en/auctions/contemporary-modern-and-old-masters-4  182 /Users/saiswarupsahu/freelanceprojectchetan/devuyst_182.csv   /Users/saiswarupsahu/freelanceprojectchetan/254 0 0
"""
TO DO:
1. Get artwork_description
2. Get price_sold
3. Get auction_start_date
4. Get auction_name
5. Get artist_nationality, if available.
"""
# supmit

