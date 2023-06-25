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


class RoBot(object):
    
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
        self.httpHeaders = { 'User-Agent' : r'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36',  'Accept' : 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8', 'Accept-Language' : 'en-us,en;q=0.5', 'Accept-Encoding' : 'gzip,deflate', 'Accept-Charset' : 'ISO-8859-1,utf-8;q=0.7,*;q=0.7', 'Keep-Alive' : '115', 'Connection' : 'keep-alive', }
        self.httpHeaders['cache-control'] = "max-age=0"
        self.httpHeaders['Pragma'] = "max-age=0"
        self.httpHeaders['Host'] = "auction.rogallery.com"
        self.httpHeaders['upgrade-insecure-requests'] = "1"
        self.httpHeaders['sec-fetch-dest'] = "document"
        self.httpHeaders['sec-fetch-mode'] = "navigate"
        self.httpHeaders['sec-fetch-site'] = "same-origin"
        self.httpHeaders['sec-fetch-user'] = "?1"
        self.homeDir = os.getcwd()
        self.requestUrl = auctionurl
        self.auctionurl = auctionurl
        parsedUrl = urlparse(self.requestUrl)
        self.baseUrl = parsedUrl.scheme + "://" + parsedUrl.netloc
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
        try:
            return(self.pageResponse.read())
        except:
            return(b"")

    def formatDate(cls, datestr):
        mondict = {'January' : '01', 'February' : '02', 'March' : '03', 'April' : '04', 'May' : '05', 'June' : '06', 'July' : '07', 'August' : '08', 'September' : '09', 'October' : '10', 'November' : '11', 'December' : '12' }
        mondict2 = {'Jan' : '01', 'Feb' : '02', 'Mar' : '03', 'Apr' : '04', 'May' : '05', 'Jun' : '06', 'Jul' : '07', 'Aug' : '08', 'Sep' : '09', 'Oct' : '10', 'Nov' : '11', 'Dec' : '12' }
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
                mm = mondict2[datestrcomponents[1]]
            except:
                pass
        yyyy = datestrcomponents[2]
        yearPattern = re.compile("\d{4}")
        if not re.search(yearPattern, yyyy):
            yyyy = "2021"
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
        titletag = soup.find("title")
        if titletag:
            titlecontent = titletag.renderContents().decode('utf-8')
            self.auctiontitle = titlecontent
            self.auctiontitle = self.auctiontitle.replace("Catalog - ", "")
            self.auctiontitle = self.auctiontitle.replace("\n", "").replace("\r", "")
        datetimespantag = soup.find("span", {'class' : 'date dateTime'})
        if datetimespantag:
            datetimecontents = datetimespantag.renderContents().decode('utf-8')
            datetimecontents = datetimecontents.replace("\n", "").replace("\r", "")
            datePattern = re.compile("([a-zA-Z]+\s+\d{1,2},\s+\d{4})")
            dps = re.search(datePattern, datetimecontents)
            if dps:
                self.auctiondate = dps.groups()[0]
        lotslistPattern = re.compile("&quot;auctionLotUserItemViewList&quot;:(\[{.*?&quot;\}\}\}\])\}")
        llps = re.search(lotslistPattern, pageContent)
        if llps:
            lotsliststr = llps.groups()[0]
            lotsliststr = lotsliststr.replace("&quot;", '"')
            lotblocks = json.loads(lotsliststr)
            return lotblocks
        return []
        

    def getDetailsPage(self, detailUrl):
        self.requestUrl = detailUrl
        self.pageRequest = urllib.request.Request(self.requestUrl, headers=self.httpHeaders)
        self.pageResponse = None
        self.postData = {}
        try:
            self.pageResponse = self.opener.open(self.pageRequest)
        except:
            print ("Error: %s"%sys.exc_info()[1].__str__())
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


    def getImage(self, imageUrl, imagepath, downloadimages):
        imageUrlParts = imageUrl.split("/")
        imagefilename = imageUrlParts[-2] + "_" + imageUrlParts[-1]
        imagedir = imageUrlParts[-2]
        backslashPattern = re.compile(r"\\")
        if downloadimages == "1":
            pageRequest = urllib.request.Request(imageUrl, headers=self.httpHeaders)
            pageResponse = None
            try:
                pageResponse = self.opener.open(pageRequest)
            except:
                print ("Error: %s"%sys.exc_info()[1].__str__())
            try:
                imageContent = pageResponse.read()
                imagefilename = backslashPattern.sub("_", imagefilename)
                ifp = open(imagepath + os.path.sep + imagefilename, "wb")
                ifp.write(imageContent)
                ifp.close()
                return imagefilename
            except:
                print("Error: %s"%sys.exc_info()[1].__str__())
        return imagefilename


    def getInfoFromLotsData(self, lotblocks, imagepath, downloadimages):
        baseUrl = "https://auction.rogallery.com"
        info = []
        endSpacePattern = re.compile("\s+$", re.DOTALL)
        beginspacePattern = re.compile("^\s+")
        emptyspacePattern = re.compile("^\s*$")
        brPattern = re.compile("<br\s*\/?>", re.IGNORECASE)
        artistPattern1 = re.compile("Artist\:\s*([^,]+),\s+([^\(]+)\s+\((\d{4})\s*\-\s*(\d{0,4})\)", re.IGNORECASE)
        titlePattern = re.compile("Title:\s+(.*)\s*$", re.IGNORECASE)
        yearPattern = re.compile("Year:\s*\w*\s*(\d{4})", re.IGNORECASE)
        mediumPattern = re.compile("Medium:\s*(.*)\s*$", re.IGNORECASE)
        editionPattern = re.compile("Edition:\s+(.*)\s*$", re.IGNORECASE)
        sizePattern1 = re.compile("Size:\s+([^\(]+)\s+\(", re.IGNORECASE)
        sizePattern2 = re.compile("Size:\s+.*?\(([^\)]+)\)", re.IGNORECASE)
        measureunitPattern = re.compile("([a-zA-Z]{2}\.?)")
        matcatdict_en = {}
        matcatdict_fr = {}
        #with open("docs/fineart_materials.csv", newline='') as mapfile:
        with open("/root/artwork/deploydirnew/docs/fineart_materials.csv", newline='') as mapfile:
            mapreader = csv.reader(mapfile, delimiter=",", quotechar='"')
            for maprow in mapreader:
                matcatdict_en[maprow[1]] = maprow[3]
                matcatdict_fr[maprow[2]] = maprow[3]
        mapfile.close()
        for lotblock in lotblocks:
            itemview = lotblock['itemView']
            data = {}
            data['auction_num'] = self.saleno
            detailUrl = ""
            lotno = str(itemview['lotNumber'])
            data['price_estimate_min'] = str(itemview['estimateLow'])
            data['price_estimate_max'] = str(itemview['estimateHigh'])
            data['lot_num'] = str(itemview['lotNumber'])
            data['lot_origin_url'] = baseUrl + itemview['linkLotURLRelative']
            data['price_sold'] = str(itemview['priceResult'])
            if data['price_sold'] == "0":
                data['price_sold'] = ""
            if itemview['medium'] != "":
                data['artwork_materials'] = itemview['medium']
            if itemview['circa'] != "":
                data['artwork_start_year'] = str(itemview['circa'])
            size = itemview['dimensions']
            data['artwork_description'] = itemview['description']
            data['artwork_description'] = data['artwork_description'].replace("&lt;", "<").replace("&gt;", ">")
            data['artwork_description'] = data['artwork_description'].replace("\n", "").replace("\r", "")
            descparts = re.split(brPattern, data['artwork_description'])
            for descpart in descparts:
                anps1 = re.search(artistPattern1, descpart)
                tps = re.search(titlePattern, descpart)
                yps = re.search(yearPattern, descpart)
                mps = re.search(mediumPattern, descpart)
                eps = re.search(editionPattern, descpart)
                zps1 = re.search(sizePattern1, descpart)
                zps2 = re.search(sizePattern2, descpart)
                if 'artist_name' not in data.keys() and anps1:
                    data['artist_name'] = anps1.groups()[0]
                    data['artist_nationality'] = anps1.groups()[1]
                    data['artist_birth'] = anps1.groups()[2]
                    data['artist_death'] = anps1.groups()[3]
                elif 'artwork_name' not in data.keys() and tps:
                    data['artwork_name'] = tps.groups()[0]
                elif 'artwork_start_year' not in data.keys() and yps:
                    data['artwork_start_year'] = yps.groups()[0]
                elif 'artwork_materials' not in data.keys() and mps:
                    data['artwork_materials'] = mps.groups()[0]
                elif 'artwork_edition' not in data.keys() and eps:
                    data['artwork_edition'] = eps.groups()[0]
                elif 'artwork_size_notes' not in data.keys() and zps1:
                    data['artwork_size_notes'] = zps1.groups()[0]
                elif 'artwork_size_notes' not in data.keys() and zps2:
                    data['artwork_size_notes'] = zps2.groups()[0]
            if 'artist_name' not in data.keys() or data['artist_name'] == "":
                data['artist_name'] = itemview['artistFullName']
            if 'artwork_name' not in data.keys() or data['artwork_name'] == "":
                data['artwork_name'] = itemview['title']
            if 'artwork_size_notes' not in data.keys() or data['artwork_size_notes'] == "":
                data['artwork_size_notes'] = itemview['dimensions']
            if 'artwork_size_notes' in data.keys():
                sizeparts = data['artwork_size_notes'].split("x")
                data['artwork_measurements_height'] = sizeparts[0]
                data['artwork_measurements_height'] = measureunitPattern.sub("", data['artwork_measurements_height'])
                if sizeparts.__len__() > 1:
                    mups = re.search(measureunitPattern, sizeparts[1])
                    if mups:
                        data['auction_measureunit'] = mups.groups()[0]
                        sizeparts[1] = measureunitPattern.sub("", sizeparts[1])
                    data['artwork_measurements_width'] = sizeparts[1]
                if sizeparts.__len__() > 2:
                    mups = re.search(measureunitPattern, sizeparts[2])
                    if mups:
                        data['auction_measureunit'] = mups.groups()[0]
                        sizeparts[2] = measureunitPattern.sub("", sizeparts[2])
                    data['artwork_measurements_depth'] = sizeparts[2]
            data['artwork_provenance'] = itemview['provenance']
            data['artwork_exhibited'] = itemview['exhibited']
            data['artwork_literature'] = itemview['literature']
            data['artwork_condition_in'] = itemview['condition']
            data['auction_house_name'] = "RoGallery"
            data['auction_location'] = "Long Island City, NY"
            data['artwork_description'] = data['artwork_description'].replace("Provenance", "<br><strong>Provenance</strong><br>")
            data['artwork_description'] = data['artwork_description'].replace("Literature", "<br><strong>Literature</strong><br>")
            data['artwork_description'] = data['artwork_description'].replace("Exhibited", "<br><strong>Exhibited</strong><br>")
            data['artwork_description'] = data['artwork_description'].replace("Expositions", "<br><strong>Expositions</strong><br>")
            data['artwork_description'] = data['artwork_description'].replace("Bibliographie", "<br><strong>Literature</strong><br>")
            data['artwork_description'] = data['artwork_description'].replace("Condition Report", "<br><strong>Condition Report</strong><br>")
            data['artwork_description'] = data['artwork_description'].replace("Notes:", "<br><strong>Notes:</strong><br>")
            data['artwork_description'] = "<strong><br>Description<br></strong>" + data['artwork_description']
            data['artwork_description'] = data['artwork_description'].replace('"', "'")
            #print(data['lot_num'] + " ## " + data['artist_name'] + " ## " + data['artwork_name'] + " ## " + data['price_estimate_min'] + " ## " + data['artwork_materials'] + " ## " + data['artwork_size_notes'])
            print("Getting '%s'..."%data['lot_origin_url'])
            if data['lot_origin_url'] == "":
                break
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
            if 'artwork_materials' in data.keys() and 'artwork_category' not in data.keys():
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
            data['auction_name'] = self.auctiontitle
            data['auction_location'] = "New York"
            if 'auction_start_date' not in data.keys():
                data['auction_start_date'] = self.auctiondate
            photos = itemview['photos']
            try:
                defaultimageurl = photos[0]['_links']['large']['href']
                imagename1 = self.getImagenameFromUrl(defaultimageurl)
                imagename1 = str(imagename1)
                imagename1 = imagename1.replace("b'", "").replace("'", "")
                auctiontitle = self.auctiontitle.replace(" ", "_")
                processedAuctionTitle = auctiontitle.replace(" ", "_")
                processedArtistName = data['artist_name'].replace(" ", "_")
                processedArtistName = unidecode.unidecode(processedArtistName)
                processedArtworkName = data['artwork_name'].replace(" ", "_")
                sublot_number = ""
                #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + self.saleno + "__" + lotno + "__" + sublot_number
                newname1 = self.saleno + "__" + processedArtistName + "__" + str(lotno) + "_a"
                #encryptedFilename = self.encryptFilename(newname1)
                encryptedFilename = newname1
                imagepathparts = defaultimageurl.split("/")
                defimageurl = "/".join(imagepathparts[:-2])
                encryptedFilename = str(encryptedFilename).replace("b'", "")
                encryptedFilename = str(encryptedFilename).replace("'", "")
                data['image1_name'] = str(encryptedFilename) + ".jpg"
                data['artwork_images1'] = defaultimageurl
            except:
                print ("Error Default Image: %s"%sys.exc_info()[1].__str__()) # Might need to check what the error is if we don't get any images.
            altimages = []
            try:
                for photo in photos[1:]:
                    altimages.append(photo['_links']['large']['href'])
            except:
                print ("Error Additional Images: %s"%sys.exc_info()[1].__str__())
            imgctr = 2
            if altimages.__len__() > 0:
                altimage2 = altimages[0]
                altimage2parts = altimage2.split("/")
                altimageurl = "/".join(altimage2parts[:-2])
                processedArtistName = data['artist_name'].replace(" ", "_")
                processedArtistName = unidecode.unidecode(processedArtistName)
                processedArtworkName = data['artwork_name'].replace(" ", "_")
                sublot_number = ""
                #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + self.saleno + "__" + lotno + "__" + sublot_number
                newname1 = self.saleno + "__" + processedArtistName + "__" + str(lotno) + "_b"
                #encryptedFilename = self.encryptFilename(newname1)
                encryptedFilename = newname1
                data['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
                data['artwork_images' + str(imgctr)] = altimage2
                imgctr += 1
            if altimages.__len__() > 1:
                altimage2 = altimages[1]
                altimage2parts = altimage2.split("/")
                altimageurl = "/".join(altimage2parts[:-2])
                processedArtistName = data['artist_name'].replace(" ", "_")
                processedArtistName = unidecode.unidecode(processedArtistName)
                processedArtworkName = data['artwork_name'].replace(" ", "_")
                sublot_number = ""
                #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + self.saleno + "__" + lotno + "__" + sublot_number
                newname1 = self.saleno + "__" + processedArtistName + "__" + str(lotno) + "_c"
                #encryptedFilename = self.encryptFilename(newname1)
                encryptedFilename = newname1
                data['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
                data['artwork_images' + str(imgctr)] = altimage2
                imgctr += 1
            if altimages.__len__() > 2:
                altimage2 = altimages[2]
                altimage2parts = altimage2.split("/")
                altimageurl = "/".join(altimage2parts[:-2])
                processedArtistName = data['artist_name'].replace(" ", "_")
                processedArtistName = unidecode.unidecode(processedArtistName)
                processedArtworkName = data['artwork_name'].replace(" ", "_")
                sublot_number = ""
                #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + self.saleno + "__" + lotno + "__" + sublot_number
                newname1 = self.saleno + "__" + processedArtistName + "__" + str(lotno) + "_d"
                #encryptedFilename = self.encryptFilename(newname1)
                encryptedFilename = newname1
                data['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
                data['artwork_images' + str(imgctr)] = altimage2
                imgctr += 1
            if altimages.__len__() > 3:
                altimage2 = altimages[3]
                altimage2parts = altimage2.split("/")
                altimageurl = "/".join(altimage2parts[:-2])
                processedArtistName = data['artist_name'].replace(" ", "_")
                processedArtistName = unidecode.unidecode(processedArtistName)
                processedArtworkName = data['artwork_name'].replace(" ", "_")
                sublot_number = ""
                #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + self.saleno + "__" + lotno + "__" + sublot_number
                newname1 = self.saleno + "__" + processedArtistName + "__" + str(lotno) + "_e"
                #encryptedFilename = self.encryptFilename(newname1)
                encryptedFilename = newname1
                data['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
                data['artwork_images' + str(imgctr)] = altimage2
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
    pageurl = "http://216.137.189.57:8080/scrapers/finish/?scrapername=RoGallery&auctionnumber=%s&auctionurl=%s&scrapertype=2"%(auctionno, urllib.parse.quote(auctionurl))
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
    robot = RoBot(auctionurl, auctionnumber)
    fp = open(csvpath, "w")
    fieldnames = ['auction_house_name', 'auction_location', 'auction_num', 'auction_start_date', 'auction_end_date', 'auction_name', 'lot_num', 'sublot_num', 'price_kind', 'price_estimate_min', 'price_estimate_max', 'price_sold', 'artist_name', 'artist_birth', 'artist_death', 'artist_nationality', 'artwork_name', 'artwork_year_identifier', 'artwork_start_year', 'artwork_end_year', 'artwork_materials', 'artwork_category', 'artwork_markings', 'artwork_edition', 'artwork_description', 'artwork_measurements_height', 'artwork_measurements_width', 'artwork_measurements_depth', 'artwork_size_notes', 'auction_measureunit', 'artwork_condition_in', 'artwork_provenance', 'artwork_exhibited', 'artwork_literature', 'artwork_images1', 'artwork_images2', 'artwork_images3', 'artwork_images4', 'artwork_images5', 'image1_name', 'image2_name', 'image3_name', 'image4_name', 'image5_name', 'lot_origin_url']
    fieldsstr = ",".join(fieldnames)
    fp.write(fieldsstr + "\n")
    pagectr = 1
    soup = BeautifulSoup(robot.currentPageContent, features="html.parser")
    while True:
        lotsdata = robot.getLotsFromPage()
        if lotsdata.__len__() == 0:
            break
        info = robot.getInfoFromLotsData(lotsdata, imagepath, downloadimages)
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
        nextpageUrl = robot.auctionurl + "?pageNum=%s"%str(pagectr)
        robot.pageRequest = urllib.request.Request(nextpageUrl, headers=robot.httpHeaders)
        try:
            robot.pageResponse = robot.opener.open(robot.pageRequest)
        except:
            print("Couldn't find the page %s"%str(pagectr))
            break
        robot.currentPageContent = robot.__class__._decodeGzippedContent(robot.getPageContent())
    fp.close()
    updatestatus(auctionnumber, auctionurl)

# Example: python rogallery.py "https://auction.rogallery.com/auction-catalog/the-art-of-the-wild_T39P2LVLZY" T39P2LVLZY /home/supmit/work/art2/ro_T39P2LVLZY.csv /home/supmit/work/art2/images/ro/T39P2LVLZY 0 0
# supmit


