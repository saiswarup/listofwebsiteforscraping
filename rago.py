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
from html.parser import HTMLParser


partialUrlPattern = re.compile("^/\w+")

def decodeHtmlEntities(content):
    entitiesDict = {'&nbsp;' : ' ', '&quot;' : '"', '&lt;' : '<', '&gt;' : '>', '&amp;' : '&', '&apos;' : "'", '&#160;' : ' ', '&#60;' : '<', '&#62;' : '>', '&#38;' : '&', '&#34;' : '"', '&#39;' : "'"}
    for entity in entitiesDict.keys():
        content = content.replace(entity, entitiesDict[entity])
    return(content)


def getContextualFilename(acctId, contextString=None):
    contextualFilename = acctId
    contextualFilename = re.sub(re.compile(r"@"), "_", contextualFilename)
    contextualFilename = re.sub(re.compile(r"\."), "_", contextualFilename)
    contextString = re.sub(re.compile(r"\s+"), "_", contextString)
    contextualFilename = contextualFilename + "_" + contextString.lower()
    return(contextualFilename)

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
        try:
            decimal = round(unicodedata.numeric(fraction), 3)
        except:
            return v
        if wholenumber:
            decimalstr = str(decimal).replace("0.", ".")
        else:
            decimalstr = str(decimal)
        value = wholenumber + decimalstr
        return value
    return v


class RagoBot(object):
    
    #startUrl=r"https://www.ragoarts.com/auctions/2021/05/post-war-contemporary-art"
    startUrl=r"https://www.ragoarts.com/auctions/2021/05/post-war-contemporary-art"
    htmltagPattern = re.compile("\<\/?[^\<\>\/]+\/?\>", re.DOTALL)
    pathEndingWithSlashPattern = re.compile(r"\/$")

    htmlEntitiesDict = {'&nbsp;' : ' ', '&#160;' : ' ', '&amp;' : '&', '&#38;' : '&', '&lt;' : '<', '&#60;' : '<', '&gt;' : '>', '&#62;' : '>', '&apos;' : '\'', '&#39;' : '\'', '&quot;' : '"', '&#34;' : '"'}

    """
    Initialization would include fetching the login page of the email service.
    """
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
        self.auctiontitle = ""
        self.auctiondate = ""


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
        mondict3 = {'Jan' : '01', 'Feb' : '02', 'Mar' : '03', 'Apr' : '04', 'May' : '05', 'Jun' : '06', 'Jul' : '07', 'Aug' : '08', 'Sep' : '09', 'Oct' : '10', 'Nov' : '11', 'Dec' : '12' }
        datestrcomponents = datestr.split(",")
        datepart = datestrcomponents[0]
        dateparts = datepart.split(" ")
        if dateparts.__len__() < 3:
            return ""
        dd = dateparts[0]
        mm = '01'
        if dateparts[1] in mondict:
            mm = mondict[dateparts[1]]
        else:
            mm = mondict3[dateparts[1]]
        yyyy = dateparts[2]
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
        baseUrl = "https://www.ragoarts.com"
        pageContent = self.currentPageContent
        soup = BeautifulSoup(pageContent, features="html.parser")
        
        datePattern = re.compile("\s+(\d{1,2}\s+[a-zA-Z]+\s+\d{4})", re.DOTALL)
        alltitletags = "American + European Art"#soup.find_all("title")
        self.auctiondate ="today"
        allMosaicAnchors = soup.find_all("&quot;alias&quot;:&quot;")
        print(allMosaicAnchors)
        return allMosaicAnchors
        

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
        detailData = {}
        metatagsPattern = re.compile('\"metatags"\:(\{[^\}]+\})\}', re.IGNORECASE|re.DOTALL)
        paperPattern = re.compile("paper", re.IGNORECASE)
        canvasPattern = re.compile("canvas", re.IGNORECASE)
        provenancePattern = re.compile("provenance", re.IGNORECASE)
        editionPattern = re.compile("edition", re.IGNORECASE)
        editionnumberPattern = re.compile("[^\d]+(\d+)[^\d]+(\d+)", re.DOTALL)
        estimatePattern = re.compile("estimate", re.IGNORECASE)
        mediumPattern = re.compile("(gold)|(silver)|(brass)|(bronze)|(wood)|(porcelain)|(stone)|(marble)|(metal)|(steel)|(iron)|(glass)|(plexiglas)|(chromogenic)|(paper)|(canvas)|(masonite)|(newsprint)|(silkscreen)|(parchment)|(linen)|(inkjet)|(ink\s+jet)|(pigment)|(\stin\s)|(photogravure)|(^oil\s+)|(\s+panel\s+)|(terracotta)|(ivory)|(\s+oak\s+)|(^oak\s+)|(\s+oak$)|(alabaster)|(polycarbonate\s+honeycomb)|(c\-print)|(acrylic)|(burlap)|(colou?r\s+photograph)|(gouache)|(terra\s+cotta)|(terracotta)|(on\s+panel)|(lithograph)|(on\s+board)|(sculpture)|(ceramic)|(photographic\s+printing)|(poster)|(dye\-transfer)|(cibachrome)", re.DOTALL|re.IGNORECASE)
        nonenglishmediumPattern = re.compile("(crayon)|(encre)|(plume)|(plume\s+et\s+encre)|(papier)|(pastel)|(craie)|(gouachée)|(aquarelle)|(lithographique)|(plomb)|(huile)|(cuivre)|(toile)|(bronze)|(Plâtre)|(en\s+terre\s+de\s+faïence)|(polycarbonate\s+alvéolaire)|(acrylique)|(jute)|(photographie\s+en\s+couleur)|(gouache)|(terre\s+cuite)|(sur\s+panneau)|(lithographie)|(sur\s+carton)|(céramique)|(cibachrome)", re.IGNORECASE|re.DOTALL)
        yearfromMediumPattern = re.compile("^\s*(\d{4})\,\s*(.*)$", re.DOTALL)
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
        mtps = re.search(metatagsPattern, detailsPage)
        if mtps:
            mtpsg = mtps.groups()
            metatagscontent = mtpsg[0]
            metatagsjson = json.loads(metatagscontent)
            imageUrl = metatagsjson['og:image']
            imageUrl = imageUrl.replace("\\", "")
            imagename1 = self.getImagenameFromUrl(imageUrl)
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
            imagepathparts = imageUrl.split("/")
            defimageurl = "/".join(imagepathparts[:-2])
            encryptedFilename = str(encryptedFilename).replace("b'", "")
            encryptedFilename = str(encryptedFilename).replace("'", "")
            detailData['image1_name'] = str(encryptedFilename) + ".jpg"
            detailData['artwork_images1'] = imageUrl
            descriptionparts = metatagsjson['description'].split(". ")
            for dp in descriptionparts:
                meps = re.search(mediumPattern, dp)
                if meps:
                    mediumcontent = dp
                    yms = re.search(yearfromMediumPattern, mediumcontent)
                    if yms:
                        ymsg = yms.groups()
                        detailData['artwork_start_year'] = ymsg[0]
                        detailData['artwork_materials'] = ymsg[1]
                    else:
                        detailData['artwork_materials'] = mediumcontent
            birthdatePattern = re.compile("Lot\s+\d+\:[\s\w]+\s+b?\.?(\d{4})[^\d]*(\d{0,4})", re.IGNORECASE|re.DOTALL)
            bds = re.search(birthdatePattern, descriptionparts[0])
            if bds:
                bdsg = bds.groups()
                detailData['artist_birth'] = bdsg[0]
                detailData['artist_death'] = bdsg[1]
            if descriptionparts.__len__() > 5:
                yearfrommedium = descriptionparts[2]
                if yearfrommedium == "c":
                    yearfrommedium = descriptionparts[3]
                yms = re.search(yearfromMediumPattern, yearfrommedium)
                if yms:
                    ymsg = yms.groups()
                    detailData['artwork_start_year'] = ymsg[0]
                    detailData['artwork_materials'] = ymsg[1]
                sizecontent = descriptionparts[3]
                if descriptionparts[2] == 'c':
                    sizecontent = descriptionparts[4]
                sizecontent = sizecontent.replace("&times;", "x")
                detailData['artwork_size_notes'] = sizecontent
                hwdPattern = re.compile("[hwd]{1}", re.IGNORECASE|re.DOTALL)
                detailData['artwork_size_notes'] = re.sub(hwdPattern, "", detailData['artwork_size_notes'])
                detailData['artwork_markings'] = descriptionparts[5]
                if descriptionparts.__len__() > 6 and not re.search(re.compile("edition", re.IGNORECASE), descriptionparts[6]) and not re.search(re.compile("provenance", re.IGNORECASE), descriptionparts[6]):
                    detailData['artwork_markings'] = detailData['artwork_markings'] + " " + descriptionparts[6]
                if descriptionparts[2] == 'c' and descriptionparts.__len__() > 6:
                    detailData['artwork_markings'] = descriptionparts[6]
                    if descriptionparts.__len__() > 7 and not re.search(re.compile("edition", re.IGNORECASE), descriptionparts[7]) and not re.search(re.compile("provenance", re.IGNORECASE), descriptionparts[7]):
                        detailData['artwork_markings'] = detailData['artwork_markings'] + " " + descriptionparts[7]
                prvs = re.search(provenancePattern, detailData['artwork_markings'])
                if prvs:
                    detailData['artwork_provenance'] = detailData['artwork_markings']
                    detailData['artwork_markings'] = ""
                estimateStringPattern = re.compile("estimate\:\s*[\$\d\,]+\&ndash;[\d\,]+", re.DOTALL)
                detailData['artwork_markings'] = estimateStringPattern.sub("", detailData['artwork_markings'])
                beginSpacePattern = re.compile("^\s+", re.DOTALL)
                detailData['artwork_markings'] = beginSpacePattern.sub("", detailData['artwork_markings'])
                if descriptionparts.__len__() > 6:
                    detailData['artwork_provenance'] = descriptionparts[6]
                    if descriptionparts[2] == 'c' and descriptionparts.__len__() > 7:
                        detailData['artwork_provenance'] = descriptionparts[7]
                    else:
                        pass
                else:
                    detailData['artwork_provenance'] = ""
                eds = re.search(editionPattern, detailData['artwork_provenance'])
                if eds:
                    detailData['artwork_edition'] = detailData['artwork_provenance']
                    detailData['artwork_provenance'] = ""
                    ens = re.search(editionnumberPattern, detailData['artwork_edition'])
                    if ens:
                        ensg = ens.groups()
                        detailData['artwork_edition'] = ensg[0]
                ess = re.search(estimatePattern, detailData['artwork_provenance'])
                if ess:
                    detailData['artwork_provenance'] = ""
                if descriptionparts.__len__() > 7:
                    prvs2 = re.search(provenancePattern, descriptionparts[7])
                    if prvs2:
                        detailData['artwork_provenance'] = descriptionparts[7]
                detailData['artwork_provenance'] = detailData['artwork_provenance'].replace("Provenance:", "")
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
            authenticityPattern = re.compile("authentic", re.IGNORECASE|re.DOTALL)
            exhibitionPattern = re.compile("exhibition", re.IGNORECASE|re.DOTALL)
            literaturePattern = re.compile("literature", re.IGNORECASE|re.DOTALL)
            measuresPattern = re.compile("(\d+[\\\w\d]*\s+h\s*\&times;\s*\d*[\\\w\d]*\s*w?\s*[\&\w;\s]*\d*[\\\w\d]*\s*d?\s*in)", re.IGNORECASE|re.DOTALL)
            birthdeathPattern = re.compile("\s+(\d{4})[\&\w;]+(\d{0,4})", re.IGNORECASE|re.DOTALL)
            for descpart in descriptionparts:
                """
                aps = re.search(authenticityPattern, descpart)
                if aps:
                      detailData['LETTEROFAUTHENTICITY'] = descpart
                """
                eps = re.search(exhibitionPattern, descpart)
                if eps:
                      detailData['artwork_exhibited'] = descpart
                lps = re.search(literaturePattern, descpart)
                if lps:
                      detailData['artwork_literature'] = descpart
                signature = ""
                if 'artwork_markings' in detailData.keys() and detailData['artwork_markings'] != "":
                    signature = detailData['artwork_markings']
                mps = re.search(measuresPattern, signature)
                if mps:
                    mpsg = mps.groups()
                    detailData['artwork_size_notes'] = mpsg[0].replace("&times;", "x")
                bps = re.search(birthdeathPattern, descpart)
                if bps and ('artist_birth' not in detailData or detailData['artist_birth'] == "") and ('artist_death' not in detailData or detailData['artist_death'] == ""):
                    bpsg = bps.groups()
                    detailData['artist_birth'] = bpsg[0]
                    detailData['artist_death'] = bpsg[1]
        if 'artwork_size_notes' in detailData.keys():
            sizeparts = detailData['artwork_size_notes'].split("x")
            detailData['artwork_measurements_height'] = sizeparts[0]
            if sizeparts.__len__() > 1:
                mups = re.search(measureunitPattern, sizeparts[1])
                if mups:
                    detailData['auction_measureunit'] = mups.groups()[0]
                    sizeparts[1] = measureunitPattern.sub("", sizeparts[1])
                detailData['artwork_measurements_width'] = sizeparts[1]
            if sizeparts.__len__() > 2:
                mups = re.search(measureunitPattern, sizeparts[2])
                if mups:
                    detailData['auction_measureunit'] = mups.groups()[0]
                    sizeparts[2] = measureunitPattern.sub("", sizeparts[2])
                detailData['artwork_measurements_depth'] = sizeparts[2]
        lotDataCachePattern = re.compile("window\.lot_data_cache\s*=\s*(\{.*\}\}\});", re.DOTALL)
        ldcs = re.search(lotDataCachePattern, detailsPage)
        if ldcs:
            ldcsg = ldcs.groups()
            ldcsm = ldcsg[0]
            ldcsjson = json.loads(ldcsm)
            ldcsdict = ldcsjson["lot_" + lotno]["item"]
            if 'literature' in ldcsdict:
                literature = str(ldcsdict['literature'])
                literature = self.__class__.htmltagPattern.sub("", literature)
                if not literature or literature == "None":
                    literature = ""
                detailData['artwork_literature'] = literature
            if 'exhibited' in ldcsdict:
                exhibition = str(ldcsdict['exhibited'])
                exhibition = self.__class__.htmltagPattern.sub("", exhibition)
                if not exhibition or exhibition == "None":
                    exhibition = ""
                detailData['artwork_exhibited'] = exhibition
        if 'artwork_size_notes' in detailData:
            detailData['artwork_size_notes'] = self.fractionToDecimalSize(detailData['artwork_size_notes'])
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
        baseUrl = "https://www.ragoarts.com"
        info = []
        thumbnailPattern = re.compile("\/120\/")
        emptyspacePattern = re.compile("^\s*$")
        for htmlanchor in htmlList:
            data = {}
            detailUrl = baseUrl + htmlanchor['href']
            htmlContent = htmlanchor.renderContents().decode('utf-8')
            s = BeautifulSoup(htmlContent, features="html.parser")
            lotspan = s.find_all("span", {'class' : 'lot_no'})
            lotno = ""
            if lotspan.__len__() > 0:
                lotno = lotspan[0].renderContents().decode('utf-8')
            artistname, title, estimate, soldforcontents = "", "", "", ""
            artistspantags = s.find_all("span", {'class' : 'name'})
            if artistspantags.__len__() > 0:
                artistspan = artistspantags[0]
                artistname = artistspan.renderContents().decode('utf-8')
                artistname = artistname.replace("\n", "").replace("\r", "")
            titledivtags = s.find_all("div", {'class' : 'title'})
            if titledivtags.__len__() > 0:
                titlediv = titledivtags[0]
                title = titlediv.renderContents().decode('utf-8')
                title = self.__class__.htmltagPattern.sub("", title)
                title = title.replace("\n", "").replace("\r", "")
            estimatedivtags = s.find_all("div", {'class' : 'estimate'})
            if estimatedivtags.__len__() > 0:
                estimatediv = estimatedivtags[0]
                estimate = estimatediv.renderContents().decode('utf-8')
                estimate = self.__class__.htmltagPattern.sub("", estimate)
                estimate = estimate.replace("\n", "").replace("\r", "")
                estimate = estimate.replace("&ndash;", " - ")
                estimate = estimate.replace("$", "")
                estimate = estimate + " USD"
            artistnameparts = artistname.split(" ")
            if artistnameparts.__len__() > 0:
                artistfirstname = artistnameparts[0]
            soldfordivtags = s.find_all("div", {'class' : 'result'})
            if soldfordivtags.__len__() > 0:
                soldforcontents = soldfordivtags[0].renderContents().decode('utf-8')
                soldforcontents = self.__class__.htmltagPattern.sub("", soldforcontents)
                soldforcontents = soldforcontents.replace("\n", "").replace("\r", "")
                soldforcontents = soldforcontents.replace("result:", "")
                soldforcontents = soldforcontents.replace("$", "")
                if not re.search(emptyspacePattern, soldforcontents):
                    soldforcontents = soldforcontents + " USD"
            data['artist_name'] = artistname
            data['lot_num'] = lotno
            data['lot_origin_url'] = detailUrl
            data['artwork_name'] = title
            estimateparts = estimate.split("–")
            data['price_estimate_min'] = estimateparts[0]
            if estimateparts.__len__() > 1:
                data['price_estimate_max'] = estimateparts[1]
                data['price_estimate_max'] = data['price_estimate_max'].replace(" USD", "")
            data['price_sold'] = soldforcontents
            #print(title + " ## " + artistname + " ## " + lotno + " ## " + detailUrl + " ## " + estimate)
            print("Fetching details from '%s'"%detailUrl)
            detailsPageContent = self.getDetailsPage(detailUrl)
            data['auction_house_name'] = "RAGO"
            alternateImageUrls = []
            alternateImageUrlsdict = {}
            srcsetPattern = re.compile('"data\-srcset":"([^"]+)"', re.DOTALL)
            index120Pattern = re.compile('"index_120":"([^"]+)"', re.DOTALL)
            datazoomsrcPattern = re.compile('"data\-zoom\-src":"([^"]+)"', re.DOTALL)
            datazoomPattern = re.compile('"data\-zoom":"([^"]+)"', re.DOTALL)
            srcsetmatches = re.findall(srcsetPattern, detailsPageContent)
            for srcsetmatch in srcsetmatches:
                if artistfirstname.lower() in srcsetmatch:
                    if srcsetmatch not in alternateImageUrlsdict.keys():
                        alternateImageUrls.append(srcsetmatch)
                        alternateImageUrlsdict[srcsetmatch] = 1
            index120matches = re.findall(index120Pattern, detailsPageContent)
            for index120match in index120matches:
                if artistfirstname.lower() in index120match:
                    if index120match not in alternateImageUrlsdict.keys():
                        alternateImageUrls.append(index120match)
                        alternateImageUrlsdict[index120match] = 1
            datazoomsrcmatches = re.findall(datazoomsrcPattern, detailsPageContent)
            for datazoomsrcmatch in datazoomsrcmatches:
                if artistfirstname.lower() in datazoomsrcmatch:
                    if datazoomsrcmatch not in alternateImageUrlsdict.keys():
                        alternateImageUrls.append(datazoomsrcmatch)
                        alternateImageUrlsdict[datazoomsrcmatch] = 1
            datazoommatches = re.findall(datazoomPattern, detailsPageContent)
            for datazoommatch in datazoommatches:
                if artistfirstname.lower() in datazoommatch:
                    if datazoommatch not in alternateImageUrlsdict.keys():
                        alternateImageUrls.append(datazoommatch)
                        alternateImageUrlsdict[datazoommatch] = 1
            j = 0
            alternateValidUrls = []
            while j < alternateImageUrls.__len__():
                imgurl = alternateImageUrls[j]
                imgurlparts = imgurl.split("?")
                altimgurl = imgurlparts[0].replace("\\", "")
                # Discard thumbnails...
                ths = re.search(thumbnailPattern, altimgurl)
                if ths:
                    j += 1
                    continue
                alternateValidUrls.append(altimgurl)
                j += 1
            imgctr = 2
            if alternateValidUrls.__len__() > 0:
                altimage2 = alternateValidUrls[0]
                altimage2parts = altimage2.split("/")
                altimageurl = "/".join(altimage2parts[:-2])
                auctiontitle = self.auctiontitle.replace(" ", "_")
                processedAuctionTitle = auctiontitle.replace(" ", "_")
                processedArtistName = artistname.replace(" ", "_")
                processedArtistName = unidecode.unidecode(processedArtistName)
                processedArtworkName = title.replace(" ", "_")
                sublot_number = ""
                #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + self.saleno + "__" + lotno + "__" + sublot_number
                newname1 = self.saleno + "__" + processedArtistName + "__" + lotno + "_b"
                #encryptedFilename = self.encryptFilename(newname1)
                encryptedFilename = newname1
                data['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
                data['artwork_images' + str(imgctr)] = altimage2
                imgctr += 1
            if alternateValidUrls.__len__() > 1:
                altimage2 = alternateValidUrls[1]
                altimage2parts = altimage2.split("/")
                altimageurl = "/".join(altimage2parts[:-2])
                auctiontitle = self.auctiontitle.replace(" ", "_")
                processedAuctionTitle = auctiontitle.replace(" ", "_")
                processedArtistName = artistname.replace(" ", "_")
                processedArtistName = unidecode.unidecode(processedArtistName)
                processedArtworkName = title.replace(" ", "_")
                sublot_number = ""
                #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + self.saleno + "__" + lotno + "__" + sublot_number
                newname1 = self.saleno + "__" + processedArtistName + "__" + lotno + "_c"
                #encryptedFilename = self.encryptFilename(newname1)
                encryptedFilename = newname1
                data['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
                data['artwork_images' + str(imgctr)] = altimage2
                imgctr += 1
            if alternateValidUrls.__len__() > 2:
                altimage2 = alternateValidUrls[2]
                altimage2parts = altimage2.split("/")
                altimageurl = "/".join(altimage2parts[:-2])
                auctiontitle = self.auctiontitle.replace(" ", "_")
                processedAuctionTitle = auctiontitle.replace(" ", "_")
                processedArtistName = artistname.replace(" ", "_")
                processedArtistName = unidecode.unidecode(processedArtistName)
                processedArtworkName = title.replace(" ", "_")
                sublot_number = ""
                #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + self.saleno + "__" + lotno + "__" + sublot_number
                newname1 = self.saleno + "__" + processedArtistName + "__" + lotno + "_d"
                #encryptedFilename = self.encryptFilename(newname1)
                encryptedFilename = newname1
                data['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
                data['artwork_images' + str(imgctr)] = altimage2
                imgctr += 1
            if alternateValidUrls.__len__() > 3:
                altimage2 = alternateValidUrls[3]
                altimage2parts = altimage2.split("/")
                altimageurl = "/".join(altimage2parts[:-2])
                auctiontitle = self.auctiontitle.replace(" ", "_")
                processedAuctionTitle = auctiontitle.replace(" ", "_")
                processedArtistName = artistname.replace(" ", "_")
                processedArtistName = unidecode.unidecode(processedArtistName)
                processedArtworkName = title.replace(" ", "_")
                sublot_number = ""
                #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + self.saleno + "__" + lotno + "__" + sublot_number
                newname1 = self.saleno + "__" + processedArtistName + "__" + lotno + "_d"
                #encryptedFilename = self.encryptFilename(newname1)
                encryptedFilename = newname1
                data['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
                data['artwork_images' + str(imgctr)] = altimage2
            detailData = self.parseDetailPage(detailsPageContent, lotno, imagepath, artistname, title, downloadimages)
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
            if 'price_sold' not in data.keys() or data['price_sold'] == "":
                data['price_sold'] = "0"
            else:
                data['price_sold'] = data['price_sold'].replace(" USD", "")
            data['auction_num'] = self.saleno
            data['auction_name'] = self.auctiontitle
            data['auction_start_date'] = self.auctiondate
            data['auction_location'] = "Lambertville, NJ"
            if 'artwork_start_year' not in data.keys():
                data['artwork_start_year'] = ""
            if 'artwork_provenance' not in data.keys():
                data['artwork_provenance'] = ""
            if 'artwork_exhibited' not in data.keys():
                data['artwork_exhibited'] = ""
            if 'artwork_literature' not in data.keys():
                data['artwork_literature'] = ""
            if 'artwork_name' not in data.keys():
                data['artwork_name'] = ""
            if 'artist_name' not in data.keys():
                data['artist_name'] = ""
            if 'artwork_size_notes' not in data.keys():
                data['artwork_size_notes'] = ""
            data['artwork_description'] = data['artwork_name'] + " " + data['artwork_start_year'] + "\t" + data['artist_name'] + "\tSize: " + data['artwork_size_notes'] + "\tProvenance: " + data['artwork_provenance'] + "\tExhibited: " + data['artwork_exhibited'] + "\tLiterature: " + data['artwork_literature']
            data['artwork_description'] = data['artwork_description'].replace("Provenance", "<br><strong>Provenance</strong><br>")
            data['artwork_description'] = data['artwork_description'].replace("Literature", "<br><strong>Literature</strong><br>")
            data['artwork_description'] = data['artwork_description'].replace("Exhibited", "<br><strong>Exhibited</strong><br>")
            data['artwork_description'] = data['artwork_description'].replace("Expositions", "<br><strong>Expositions</strong><br>")
            data['artwork_description'] = data['artwork_description'].replace("Bibliographie", "<br><strong>Literature</strong><br>")
            data['artwork_description'] = data['artwork_description'].replace("Condition Report", "<br><strong>Condition Report</strong><br>")
            data['artwork_description'] = data['artwork_description'].replace("Notes:", "<br><strong>Notes:</strong><br>")
            data['artwork_description'] = "<strong><br>Description<br></strong>" + data['artwork_description']
            data['artwork_description'] = data['artwork_description'].replace('"', "'")
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
    pageurl = "http://216.137.189.57:8080/scrapers/finish/?scrapername=Rago&auctionnumber=%s&auctionurl=%s&scrapertype=2"%(auctionno, urllib.parse.quote(auctionurl))
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
    rago = RagoBot(auctionurl, auctionnumber)
    print(rago)
    fp = open(csvpath, "w")
    fieldnames = ['auction_house_name', 'auction_location', 'auction_num', 'auction_start_date', 'auction_end_date', 'auction_name', 'lot_num', 'sublot_num', 'price_kind', 'price_estimate_min', 'price_estimate_max', 'price_sold', 'artist_name', 'artist_birth', 'artist_death', 'artist_nationality', 'artwork_name', 'artwork_year_identifier', 'artwork_start_year', 'artwork_end_year', 'artwork_materials', 'artwork_category', 'artwork_markings', 'artwork_edition', 'artwork_description', 'artwork_measurements_height', 'artwork_measurements_width', 'artwork_measurements_depth', 'artwork_size_notes', 'auction_measureunit', 'artwork_condition_in', 'artwork_provenance', 'artwork_exhibited', 'artwork_literature', 'artwork_images1', 'artwork_images2', 'artwork_images3', 'artwork_images4', 'artwork_images5', 'image1_name', 'image2_name', 'image3_name', 'image4_name', 'image5_name', 'lot_origin_url']
    fieldsstr = ",".join(fieldnames)
    fp.write(fieldsstr + "\n")
    lotsdata = rago.getLotsFromPage()
    print(lotsdata)
    info = rago.getInfoFromLotsData(lotsdata, imagepath, downloadimages)
    lotctr = 0 
    for d in info:
        lotctr += 1
        for f in fieldnames:
            if f in d and d[f] is not None:
                fp.write('"' + str(d[f]) + '",')
            else:
                fp.write('"",')
        fp.write("\n")
    fp.close()
    updatestatus(auctionnumber, auctionurl)

# Example: python rago.py https://www.ragoarts.com/auctions/2019/11/american-european-art  20190120   /Users/saiswarupsahu/freelanceprojectchetan/rago_20190120.csv  /Users/saiswarupsahu/freelanceprojectchetan/ 0 0
# supmit

