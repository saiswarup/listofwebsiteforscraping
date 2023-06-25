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
from socket import timeout

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


class DesaBot(object):
    
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
        self.httpHeaders = { 'User-Agent' : r'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36',  'Accept' : 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9', 'Accept-Language' : 'en-us,en;q=0.5', 'Accept-Encoding' : 'gzip,deflate', 'Accept-Charset' : 'ISO-8859-1,utf-8;q=0.7,*;q=0.7', 'Connection' : 'keep-alive', }
        self.httpHeaders['cache-control'] = "max-age=0"
        self.httpHeaders['sec-ch-ua'] = "\".Not/A)Brand\";v=\"99\", \"Google Chrome\";v=\"103\", \"Chromium\";v=\"103\""
        self.httpHeaders['sec-ch-ua-mobile'] = "?0"
        self.httpHeaders['sec-ch-ua-platform'] = "Linux"
        self.httpHeaders['upgrade-insecure-requests'] = "1"
        self.httpHeaders['sec-fetch-dest'] = "document"
        self.httpHeaders['sec-fetch-mode'] = "navigate"
        self.httpHeaders['sec-fetch-site'] = "none"
        self.httpHeaders['sec-fetch-user'] = "?1"
        #self.httpHeaders['cookie'] = "_gcl_au=1.1.1798205744.1657777147; _fbp=fb.1.1657777148507.1276226155; django_language=en; csrftoken=XxquXWx4l73ds7TAnekDoWucweL6TMEh2HnRSdEqn2plvEjo5NpLf8DiXIoH8Aqg; sessionid=7xvmblkrfug8iec9q974p25vasvxgsb3; CookieConsent={stamp:'HB7TMwV9wUptvBPR7L0vSZU/cKw0H3tsejN1PQtTPnGjZ4+Nnuhdhg==',necessary:true,preferences:true,statistics:true,marketing:true,ver:1,utc:1657780443613,region:'in'}; _hjSessionUser_2713844=eyJpZCI6IjUzOTY5YWZjLTVkMmQtNWVhZC1iM2RkLTMyMzRjZTlhZTliOSIsImNyZWF0ZWQiOjE2NTc3ODA0NDQyNTgsImV4aXN0aW5nIjpmYWxzZX0=; _ga=GA1.2.1776879080.1657777147; gtm_user_form_id=8225709787964e0fb02d9c7ae97662b3; _ga_69TX98NVSJ=GS1.1.1657864748.3.0.1657864748.60; DO-LB=\"MTAuMTM1LjIyMi4xMDU6NDQz\""
        self.homeDir = os.getcwd()
        self.auctionurl = auctionurl
        self.requestUrl = auctionurl
        parsedUrl = urlparse(self.requestUrl)
        self.baseUrl = parsedUrl.scheme + "://" + parsedUrl.netloc
        self.httpHeaders['Host'] = parsedUrl.netloc
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
        metatag = soup.find("meta", {'name' : 'twitter:url'})
       
        desaPattern = re.compile("\s+sale", re.IGNORECASE|re.DOTALL)
        if metatag is not None:
            self.auctiontitle = metatag['content']
            self.auctiontitle = re.split(desaPattern, self.auctiontitle)[0]
            self.auctiontitle = self.auctiontitle.replace('"', "'")
        divPattern = re.compile("^desa\-object\s+debug__object\-published\-\-True\s+.*$", re.DOTALL)
        bidPattern = re.compile("bid\.")
        if re.search(bidPattern, self.baseUrl):
            metatag = soup.find("meta", {'name' : 'title'})
            if metatag is not None:
                self.auctiontitle = metatag['content']
            viewvarsPattern = re.compile("viewVars\s+=\s*(\{.*\});\s*")
            vps = re.search(viewvarsPattern, pageContent)
            if vps:
                datadict = json.loads(vps.groups()[0])
                #print(str(datadict['lots']['result_page'][0]['lot_number']) + " " + datadict['lots']['result_page'][0]['title'] + " " + datadict['lots']['result_page'][0]['dimensions'])
                return datadict['lots']['result_page']
            else:
                lotdivtags = []
        else:
            lotdivtags = soup.find_all("div", {'class' : divPattern})
        datePattern = re.compile("(\d{1,2}\s+[a-zA-Z]+\s+\d{4})", re.DOTALL)
        datedivtags = soup.find_all("div", {'class' : 'simple-content__info'})
        for datedivtag in datedivtags:
            dateptag = datedivtag.find("p")
            if dateptag:
                datecontent = dateptag.renderContents().decode('utf-8')
                dps = re.search(datePattern, datecontent)
                if dps:
                    self.auctiondate = dps.groups()[0]
                    break
        return lotdivtags
        

    def getDetailsPage(self, detailUrl):
        self.requestUrl = detailUrl
        self.pageRequest = urllib.request.Request(self.requestUrl, headers=self.httpHeaders)
        self.pageResponse = None
        self.postData = {}
        try:
            self.pageResponse = self.opener.open(self.pageRequest, timeout=10)
            #response = requests.get(self.requestUrl, headers=self.httpHeaders, timeout=10)
            #headers = self.pageResponse.getheaders()
        except:
            print ("Couldn't fetch page due to limited connectivity. Please check your internet connection and try again. %s"%sys.exc_info()[1].__str__())
            return ""
        self.currentPageContent = self.__class__._decodeGzippedContent(self.getPageContent())
        #self.currentPageContent = response.text
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
        detailData = {}
        brPattern = re.compile("<br\s*\/?>")
        beginspacePattern = re.compile("^\s+")
        endspacePattern = re.compile("\s+$")
        endcommaPattern = re.compile(",\s*$")
        literaturePattern = re.compile("Bibliographie", re.IGNORECASE|re.DOTALL)
        provenancePattern = re.compile("PROVENANCE", re.IGNORECASE|re.DOTALL)
        editionPattern = re.compile("(es\.\s+\d+\/\d+)", re.IGNORECASE|re.DOTALL)
        sizePattern1 = re.compile("([\d\sx\.,]+)\s+(cm)", re.DOTALL)
        sizePattern2 = re.compile("([\d\sx\.,]+)\s+(in)", re.DOTALL)
        sizePattern3 = re.compile("([\d\sx\.,\/]+)\s+(cm)", re.DOTALL)
        sizePattern4 = re.compile("([\d\sx\.,\/]+)\s+(in)", re.DOTALL)
        mediumPattern = re.compile("(gold)|(silver)|(brass)|(bronze)|(wood)|(porcelain)|(stone)|(marble)|(metal)|(steel)|(iron)|(glass)|(plexiglas)|(chromogenic)|(paper)|(canvas)|(masonite)|(newsprint)|(silkscreen)|(parchment)|(linen)|(inkjet)|(ink\s+jet)|(pigment)|(\stin\s)|(photogravure)|(^oil\s+)|(\s+panel\s+)|(terracotta)|(ivory)|(\s+oak\s+)|(^oak\s+)|(\s+oak$)|(alabaster)|(\s+ink\s+)|(pencil)|(albumen)|(oil\s+)|(\s+oil)|(panel)|(acrylic)|(print)|(Huile)|(toile)|(plume)|(encre)|(lavis)|(Gravure)|(Pierre)|(pastel)|(panneau)|(Sanguine)|(Crayon)|(aquarelle)|(papier)", re.DOTALL|re.IGNORECASE)
        signedPattern1 = re.compile("(signed[^\.]+)[\.,\w\s;]*$")
        signedPattern2 = re.compile("(authored[^\.]+)[\.,\w\s;]*$")
        yearPattern = re.compile("(\d{4})")
        imgurlPattern = re.compile("\"image\"\: \"([^\"]+)\"", re.DOTALL)
        dotPattern = re.compile("\w+\.[\s\w]+", re.DOTALL)
        soup = BeautifulSoup(detailsPage, features="html.parser")
        if 'bid.' in self.baseUrl:
            imagePattern = re.compile("\"image\"\:(\[.*?\])", re.DOTALL)
            ips = re.search(imagePattern, detailsPage)
            if ips:
                images = json.loads(ips.groups()[0])
                imgurllist = []
                for imgurl in images:
                    imgurl = imgurl.replace("\/", "/")
                    imgurllist.append(imgurl)
                imgurl = imgurllist[0]
                imagename1 = self.getImagenameFromUrl(imgurl)
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
                imagepathparts = imgurl.split("/")
                defimageurl = "/".join(imagepathparts[:-2])
                encryptedFilename = str(encryptedFilename).replace("b'", "")
                encryptedFilename = str(encryptedFilename).replace("'", "")
                detailData['image1_name'] = str(encryptedFilename) + ".jpg"
                detailData['artwork_images1'] = imgurl
            return detailData
        try:
            desccontents = soup.find("meta", {'name' : 'description'})['content']
        except:
            desccontents = ""
        if desccontents:
            sps1 = re.search(signedPattern1, desccontents)
            sps2 = re.search(signedPattern2, desccontents)
            if sps1:
                detailData['artwork_markings'] = sps1.groups()[0]
                detailData['artwork_markings'] = detailData['artwork_markings'].replace('"', "'").replace(";", ".")
            elif sps2:
                detailData['artwork_markings'] = sps2.groups()[0]
                detailData['artwork_markings'] = detailData['artwork_markings'].replace('"', "'").replace(";", ".")
        ips = re.search(imgurlPattern, detailsPage)
        if ips:
            imgurl = ips.groups()[0]
            if not imgurl.startswith('https://'):
                imgurl = self.baseUrl + imgurl
            imagename1 = self.getImagenameFromUrl(imgurl)
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
            imagepathparts = imgurl.split("/")
            defimageurl = "/".join(imagepathparts[:-2])
            encryptedFilename = str(encryptedFilename).replace("b'", "")
            encryptedFilename = str(encryptedFilename).replace("'", "")
            detailData['image1_name'] = str(encryptedFilename) + ".jpg"
            detailData['artwork_images1'] = imgurl
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
        baseUrl = "https://bid.desa.pl"
        info = []
        endSpacePattern = re.compile("\s+$", re.DOTALL)
        soldpricePattern = re.compile("([\d\s\.,]+)\s+€")
        beginspacePattern = re.compile("^\s+")
        sizePattern1 = re.compile("([\d\sx\.,]+)\s+(cm)", re.DOTALL)
        sizePattern2 = re.compile("([\d\sx\.,]+)\s+(in)", re.DOTALL)
        sizePattern3 = re.compile("([\d\sx\.,\/]+)\s+(cm)", re.DOTALL)
        sizePattern4 = re.compile("([\d\sx\.,\/]+)\s+(in)", re.DOTALL)
        mediumPattern = re.compile("(gold)|(silver)|(brass)|(bronze)|(wood)|(porcelain)|(stone)|(marble)|(metal)|(steel)|(iron)|(glass)|(plexiglas)|(chromogenic)|(paper)|(canvas)|(masonite)|(newsprint)|(silkscreen)|(parchment)|(linen)|(inkjet)|(ink\s+jet)|(pigment)|(\stin\s)|(photogravure)|(^oil\s+)|(\s+panel\s+)|(terracotta)|(ivory)|(\s+oak\s+)|(^oak\s+)|(\s+oak$)|(alabaster)|(\s+ink\s+)|(pencil)|(albumen)|(oil\s+)|(\s+oil)|(panel)|(acrylic)|(print)|(Huile)|(toile)|(plume)|(encre)|(lavis)|(Gravure)|(Pierre)|(pastel)|(panneau)|(Sanguine)|(Crayon)|(aquarelle)|(papier)|(gouache)|(cardboard)|(mixed\s+media)|(watercolou?r)|(tempera)|(ziemia)|(gelatin)|(baryta\s+paper)|(crayon)|(akryl)|(płótno)|(olej\s+)|(\s+olej)|(olej\/)|(litografia)|(papier)|(druk)|(inkografia)|(srebro)|(brąz)|(kamień)|(patynowany)|(trawertyn)|(tektura)|(dublowane)", re.DOTALL|re.IGNORECASE)
        signaturePattern = re.compile("(sygnowany)|(Getekend)|(Signatuur)", re.IGNORECASE)
        estimatePattern1 = re.compile("Schatting\:\s*\&([lg]{1})t;\s*€\s*(\d+)", re.IGNORECASE|re.DOTALL)
        estimatePattern2 = re.compile("Schatting\:\s*€\s*(\d+)\s*\-\s*(\d+)", re.IGNORECASE|re.DOTALL)
        soldpricePattern = re.compile("Hamerprijs\:\s*€\s*(\d+)")
        bdPattern1 = re.compile("\((\d{4})\s*\-\s*(\d{4})\)")
        bdPattern2 = re.compile("\(b[\.orn]{1,3}\s+(\d{4})\)")
        measureunitPattern = re.compile("\s([a-zA-Z]{2})\.?")
        yearPattern = re.compile("(\d{4})")
        endcommaPattern = re.compile(",\s*$")
        begincommaPattern = re.compile("^\s*,\s*")
        brPattern = re.compile("<br\s*\/?>", re.DOTALL|re.IGNORECASE)
        matcatdict_en = {}
        matcatdict_fr = {}
        with open("docs/fineart_materials.csv", newline='') as mapfile:
        #with open("/Users/saiswarupsahu/freelanceprojectchetan/docs/fineart_materials.csv", newline='') as mapfile:
            mapreader = csv.reader(mapfile, delimiter=",", quotechar='"')
            for maprow in mapreader:
                matcatdict_en[maprow[1]] = maprow[3]
                matcatdict_fr[maprow[2]] = maprow[3]
        mapfile.close()
        if "bid." in self.baseUrl: # So we would be getting a list of dicts in htmldivtags
            for lotinfo in htmldivtags:
                data = {}
                data['lot_num'], data['artist_name'], data['artist_birth'], data['artist_death'], data['artwork_name'], data['artwork_measurements_height'], data['artwork_measurements_width'], data['artwork_measurements_depth'], data['artwork_materials'], data['price_estimate_min'], data['price_estimate_max'], data['price_sold'], data['artwork_markings'] = "", "", "", "", "", "", "", "", "", "", "", "", ""
                data['auction_num'] = self.saleno
                data['auction_location'] = self.auctionlocation
                data['auction_name'] = self.auctiontitle
                self.auctiondate = endSpacePattern.sub("", self.auctiondate)
                self.auctiondate = beginspacePattern.sub("", self.auctiondate)
                data['auction_start_date'] = self.auctiondate
                data['auction_house_name'] = "Desa"
                lotno = ""
                detailUrl = ""
                lotno = str(lotinfo['lot_number'])
                data['lot_num'] = lotno
                title = lotinfo['title']
                data['artwork_name'] = title
                if data['artwork_name'] is None:
                    data['artwork_name'] = ""
                data['artwork_name'] = data['artwork_name'].replace('"', "'")
                yps = re.search(yearPattern, data['artwork_name'])
                if yps:
                    data['artwork_start_year'] = yps.groups()[0]
                    data['artwork_name'] = yearPattern.sub("", data['artwork_name'])
                if 'artwork_start_year' not in data.keys() or data['artwork_start_year'] is None:
                    data['artwork_start_year'] = ""
                artistinfo = lotinfo['artist']
                #artistinfo = lotinfo['name']
                try:
                    bdps1 = re.search(bdPattern1, artistinfo)
                    bdps2 = re.search(bdPattern2, artistinfo)
                    if bdps1:
                        data['artist_birth'] = bdps1.groups()[0]
                        data['artist_death'] = bdps1.groups()[1]
                        artistinfo = bdPattern1.sub("", artistinfo)
                        data['artist_name'] = artistinfo
                    elif bdps2: 
                        data['artist_birth'] = bdps2.groups()[0]
                        data['artist_death'] = ""
                        artistinfo = bdPattern2.sub("", artistinfo)
                        data['artist_name'] = artistinfo
                    else:
                        data['artist_name'] = artistinfo
                        data['artist_birth'] = ""
                        data['artist_death'] = ""
                except:
                    pass
                
                detailUrl = self.baseUrl + lotinfo['_detail_url']
                data['lot_origin_url'] = detailUrl
                data['artwork_size_notes'] = lotinfo['dimensions']
                if data['artwork_size_notes'] is None:
                    data['artwork_size_notes'] = ""
                data['price_estimate_min'] = lotinfo['estimate_low']
                if data['price_estimate_min'] is None:
                    data['price_estimate_min'] = ""
                data['price_estimate_max'] = lotinfo['estimate_high']
                if data['price_estimate_max'] is None:
                    data['price_estimate_max'] = ""
                data['price_sold'] = lotinfo['sold_price']
                if data['price_sold'] is None:
                    data['price_sold'] = ""
                data['artwork_condition_in'] = lotinfo['condition']
                data['artwork_description'] = lotinfo['truncated_description']
                descparts = data['artwork_description'].split(",")
                data['artwork_materials'] = ""
                data['artwork_markings'] = ""
                for descpart in descparts:
                    mps = re.search(mediumPattern, descpart)
                    sps = re.search(signaturePattern, descpart)
                    if mps:
                        data['artwork_materials'] += descpart + ","
                    if sps:
                        data['artwork_markings'] += descpart + ","
                data['artwork_materials'] = endcommaPattern.sub("", data['artwork_materials'])
                data['artwork_markings'] = endcommaPattern.sub("", data['artwork_markings'])
                matparts = re.split(brPattern, data['artwork_materials'])
                if matparts.__len__() > 1:
                    if matparts[1] != "":
                        data['artwork_materials'] = matparts[1]
                    elif matparts[-1] != "":
                        data['artwork_materials'] = matparts[-1]
                    #print(data['artwork_materials'])
                data['artwork_name'] = data['artwork_name'].replace('"', "'").replace(data['artist_name'],"").replace("(","").replace(")","").replace("-","").replace("|","").replace(",","").strip()
                print( data['artwork_name'])
                print("Getting '%s'..."%detailUrl)
                if detailUrl != "":
                    detailsPageContent = self.getDetailsPage(detailUrl)
                else:
                    detailsPageContent = ""
                if detailsPageContent == "":
                    continue
                detailData = self.parseDetailPage(detailsPageContent, data['artist_name'], data['artwork_name'], self.saleno, lotno, imagepath, downloadimages)
                for k in detailData.keys():
                    data[k] = detailData[k]
                #data['artwork_description'] = data['artwork_name'] + " " + data['artist_name'] + " " + data['artwork_materials'] + " " + data['artwork_markings'] + " " + data['artwork_size_notes'] + " Estimate: " + data['price_estimate_min'] + " - " + data['price_estimate_max'] + " Sold Price: " + data['price_sold']
                data['artwork_description'] = data['artwork_description'].replace("Provenance", "<br><strong>Provenance</strong><br>")
                data['artwork_description'] = data['artwork_description'].replace("Literature", "<br><strong>Literature</strong><br>")
                data['artwork_description'] = data['artwork_description'].replace("Exhibited", "<br><strong>Exhibited</strong><br>")
                data['artwork_description'] = data['artwork_description'].replace("Exposition", "<br><strong>Expositions</strong><br>")
                data['artwork_description'] = data['artwork_description'].replace("Bibliographie", "<br><strong>Literature</strong><br>")
                data['artwork_description'] = data['artwork_description'].replace("Condition report", "<br><strong>Condition Report</strong><br>")
                data['artwork_description'] = data['artwork_description'].replace("Notes:", "<br><strong>Notes:</strong><br>")
                data['artwork_description'] = "<strong><br>Description<br></strong>" + data['artwork_description']
                data['artwork_description'] = data['artwork_description'].replace('"', "'")
                data['artwork_measurements_height']="0"
                data['artwork_measurements_width']="0"
                data['artwork_measurements_depth']="0"
                if 'artwork_size_notes' in data.keys():
                    sizeparts = data['artwork_size_notes'].split("x")
                    if sizeparts.__len__() > 0:
                        data['artwork_measurements_height'] = sizeparts[0]
                        mups = re.search(measureunitPattern, data['artwork_measurements_height'])
                        if mups:
                            data['auction_measureunitPattern'] = mups.groups()[0]
                            data['artwork_measurements_height'] = measureunitPattern.sub("", data['artwork_measurements_height'])
                    if sizeparts.__len__() > 1:
                        data['artwork_measurements_width'] = sizeparts[1]
                        mups = re.search(measureunitPattern, data['artwork_measurements_width'])
                        if mups:
                            data['auction_measureunitPattern'] = mups.groups()[0]
                            data['artwork_measurements_width'] = measureunitPattern.sub("", data['artwork_measurements_width'])
                    if sizeparts.__len__() > 2:
                        data['artwork_measurements_depth'] = sizeparts[2]
                        mups = re.search(measureunitPattern, data['artwork_measurements_depth'])
                        if mups:
                            data['auction_measureunitPattern'] = mups.groups()[0]
                            data['artwork_measurements_depth'] = measureunitPattern.sub("", data['artwork_measurements_depth'])
                try:
                    data['artwork_measurements_height']="".join(re.findall("((?:\d+(?:\.\d*)?|\.\d+))",data['artwork_measurements_height']))
                except:
                    pass
                try:
                    data['artwork_measurements_width']="".join(re.findall("((?:\d+(?:\.\d*)?|\.\d+))",data['artwork_measurements_width']))
                except:
                    pass
                try:
                    data['artwork_measurements_depth']="".join(re.findall("((?:\d+(?:\.\d*)?|\.\d+))",data['artwork_measurements_depth']))
                except:
                    pass

                data['artwork_size_notes']=data['artwork_measurements_height']+"x"+data['artwork_measurements_width']+"x"+data['artwork_measurements_depth'] +" "+"cm"
                print(data['artwork_size_notes'])
                if 'price_sold' not in data.keys() or data['price_sold'] == "":
                    data['price_sold'] = ""
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
                    beginspacePattern = re.compile("^\s+")
                    endspacePattern = re.compile("\s+$")
                    materials = data['artwork_materials']
                    materialparts = materials.split(" ")
                    catfound = 0
                    for matpart in materialparts:
                        #print(matpart)
                        if matpart in ['in', 'on', 'of', 'the', 'from']:
                            continue
                        try:
                            matPattern = re.compile(matpart, re.IGNORECASE|re.DOTALL)
                            for enkey in matcatdict_en.keys():
                                if re.search(matPattern, enkey):
                                    data['artwork_category'] = matcatdict_en[enkey]
                                    if data['artwork_category'] == "material_category":
                                        data['artwork_category'] = "Unknown"
                                    catfound = 1
                                    break
                            for frkey in matcatdict_fr.keys():
                                if re.search(matPattern, frkey):
                                    data['artwork_category'] = matcatdict_fr[frkey]
                                    if data['artwork_category'] == "material_category":
                                        data['artwork_category'] = "Unknown"
                                    catfound = 1
                                    break
                            if catfound:
                                break
                        except:
                            pass
                data['auction_measureunit']="cm"
                data['artist_name']=data['artist_name'].replace(",",".")
                data['artist_birth']=data['artist_birth'].replace(",",".")
                data['artist_death']=data['artist_death'].replace(",",".")
                data['artwork_name']=data['artwork_name'].replace(",",".")
                data['artwork_measurements_height']=data['artwork_measurements_height'].replace(",",".")
                data['artwork_measurements_width']=data['artwork_measurements_width'].replace(",",".")
                data['artwork_measurements_depth']=data['artwork_measurements_depth'].replace(",",".")
                data['artwork_materials']=data['artwork_materials'].replace(",",".")
                data['price_estimate_min']=data['price_estimate_min'].replace(",","")
                data['price_estimate_max']=data['price_estimate_max'].replace(",","")
                data['price_sold']=data['price_estimate_max'].replace(",",".")
                data['artwork_markings'] = data['artwork_markings'].replace(",",".")
                info.append(data)
            return info
        for htmldiv in htmldivtags:
            data = {}
            data['lot_num'], data['artist_name'], data['artist_birth'], data['artist_death'], data['artwork_name'], data['artwork_measurements_height'], data['artwork_measurements_width'], data['artwork_measurements_depth'], data['artwork_materials'], data['price_estimate_min'], data['price_estimate_max'], data['price_sold'], data['artwork_markings'] = "", "", "", "", "", "", "", "", "", "", "", "", ""
            data['auction_num'] = self.saleno
            data['auction_location'] = self.auctionlocation
            data['auction_name'] = self.auctiontitle
            self.auctiondate = endSpacePattern.sub("", self.auctiondate)
            self.auctiondate = beginspacePattern.sub("", self.auctiondate)
            data['auction_start_date'] = self.auctiondate
            data['auction_house_name'] = "Desa"
            lotno = ""
            detailUrl = ""
            htmlContent = htmldiv.renderContents().decode('utf-8')
            s = BeautifulSoup(htmlContent, features="html.parser")
            lotnodiv = s.find("div", {'class' : 'box-object-row__prename'})
            if lotnodiv is not None:
                lotno = lotnodiv.renderContents().decode('utf-8')
                lotno = lotno.replace("\n", "").replace("\r", "")
                lotno = endSpacePattern.sub("", lotno)
                lotno = beginspacePattern.sub("", lotno)
                data['lot_num'] = lotno
            else:
                continue
            artistdivtag = s.find("div", {'class' : 'box-object-row__title'})
            detailUrl = ""
            if artistdivtag is not None:
                artistcontents = artistdivtag.renderContents().decode('utf-8')
                artistcontents = artistcontents.replace("\n", "").replace("\r", "")
                artistcontents = self.__class__.htmltagPattern.sub("", artistcontents)
                artistname = beginspacePattern.sub("", artistcontents)
                artistnameparts = re.split("\s{3,}", artistname)
                artistname = artistnameparts[0]
                bdps1 = re.search(bdPattern1, artistname)
                bdps2 = re.search(bdPattern2, artistname)
                if bdps1:
                    data['artist_birth'] = bdps1.groups()[0]
                    data['artist_death'] = bdps1.groups()[1]
                    artistname = bdPattern1.sub("", artistname)
                elif bdps2:
                    data['artist_birth'] = bdps2.groups()[0]
                    data['artist_death'] = ""
                    artistname = bdPattern2.sub("", artistname)
                data['artist_name'] = artistname
                data['artist_name'] = data['artist_name'].replace('"', "'")
            titletag = s.find("div", {'class' : 'box-object-row__subtitle'})
            if titletag is not None:
                titlecontents = titletag.renderContents().decode('utf-8')
                titlecontents = titlecontents.replace("\n", "").replace("\r", "")
                titlecontents = self.__class__.htmltagPattern.sub("", titlecontents)
                titlecontents = beginspacePattern.sub("", titlecontents)
                titlecontents = endSpacePattern.sub("", titlecontents)
                yps = re.search(yearPattern, titlecontents)
                if yps:
                    data['artwork_start_year'] = yps.groups()[0]
                    titlecontents = yearPattern.sub("", titlecontents)
                titlecontents = endcommaPattern.sub("", titlecontents)
                data['artwork_name'] = titlecontents
                data['artwork_name'] = data['artwork_name'].replace('"', "'").replace(data['artist_name'],"").replace("(","").replace(")","").replace("-","").replace("|","").title()
            anchortag = s.find("a")
            if anchortag is not None:
                detailUrl = self.baseUrl + anchortag['href']
            else:
                continue
            data['lot_origin_url'] = detailUrl
            detailsdivtag = s.find("div", {'class' : 'box-object-row__description'})
            if detailsdivtag is not None:
                descdivtag = detailsdivtag.find("div", {'class' : 'box-object-row__info'})
                if descdivtag is not None:
                    desccontents = descdivtag.renderContents().decode('utf-8')
                    desccontents = desccontents.replace("\n", "").replace("\r", "")
                    desccontents = self.__class__.htmltagPattern.sub("", desccontents)
                    desccontents = beginspacePattern.sub("", desccontents)
                    desccontents = endSpacePattern.sub("", desccontents)
                    zps1 = re.search(sizePattern1, desccontents)
                    zps2 = re.search(sizePattern2, desccontents)
                    zps3 = re.search(sizePattern3, desccontents)
                    zps4 = re.search(sizePattern4, desccontents)
                    if zps1:
                        data['artwork_size_notes'] = zps1.groups()[0] + " " + zps1.groups()[1]
                        data['artwork_size_notes'] = begincommaPattern.sub("", data['artwork_size_notes'])
                        data['auction_measureunit'] = zps1.groups()[1] 
                    elif zps2:
                        data['artwork_size_notes'] = zps2.groups()[0] + " " + zps2.groups()[1]
                        data['artwork_size_notes'] = begincommaPattern.sub("", data['artwork_size_notes'])
                        data['auction_measureunit'] = zps2.groups()[1]
                    elif zps3:
                        data['artwork_size_notes'] = zps3.groups()[0] + " " + zps3.groups()[1]
                        data['artwork_size_notes'] = begincommaPattern.sub("", data['artwork_size_notes'])
                        data['auction_measureunit'] = zps3.groups()[1]
                    elif zps4:
                        data['artwork_size_notes'] = zps4.groups()[0] + " " + zps4.groups()[1]
                        data['artwork_size_notes'] = begincommaPattern.sub("", data['artwork_size_notes'])
                        data['auction_measureunit'] = zps4.groups()[1]
                    desccontentparts = desccontents.split(",")
                    data['artwork_materials'] = ""
                    for descpart in desccontentparts:
                        mps = re.search(mediumPattern, descpart)
                        if mps:
                            data['artwork_materials'] = data['artwork_materials'] + descpart + ","
                    data['artwork_materials'] = endcommaPattern.sub("", data['artwork_materials'])
                    pricetag = descdivtag.find("span", {'class' : 'desa-object__price-label'})
                    if pricetag is not None:
                        pricecontent = pricetag.renderContents().decode('utf-8')
                        hammerPattern = re.compile("Hammer", re.IGNORECASE|re.DOTALL)
                        estimatePattern = re.compile("Estimate", re.IGNORECASE|re.DOTALL)
                        valuespantag = descdivtag.find("span", {'class' : 'desa-object__price-value'})
                        if valuespantag is not None:
                            pricevalue = valuespantag.renderContents().decode('utf-8')
                            pricevalue = pricevalue.replace("\n", "").replace("\r", "")
                            pricevalue = self.__class__.htmltagPattern.sub("", pricevalue)
                            pricevalue = beginspacePattern.sub("", pricevalue)
                            pricevalue = endSpacePattern.sub("", pricevalue)
                            tps = re.search(hammerPattern, pricecontent)
                            if tps:
                                data['price_sold'] = pricevalue
                            else:
                                tps = re.search(estimatePattern, pricecontent)
                                if tps:
                                    priceparts = pricevalue.split("-")
                                    data['price_estimate_min'] = priceparts[0]
                                    if priceparts.__len__() > 1:
                                        data['price_estimate_max'] = priceparts[1]
            data['artwork_name'] = data['artwork_name'].replace("(","").replace(")","").replace("-","").replace("|","")
            print( data['artwork_name'] )
            print("Getting '%s'..."%data['lot_origin_url'])
            if detailUrl != "":
                detailsPageContent = self.getDetailsPage(detailUrl)
            else:
                detailsPageContent = ""
            if detailsPageContent == "":
                continue
            detailData = self.parseDetailPage(detailsPageContent, data['artist_name'], data['artwork_name'], self.saleno, lotno, imagepath, downloadimages)
            for k in detailData.keys():
                if k == 'artwork_name' and k in data.keys() and data[k] != "":
                    continue
                else:
                    data[k] = detailData[k]
            data['artwork_description'] = data['artwork_name'] + " " + data['artist_name'] + " " + data['artwork_materials'] + " " + data['artwork_markings'] + " " + data['artwork_size_notes'] + " Estimate: " + data['price_estimate_min'] + " - " + data['price_estimate_max'] + " Sold Price: " + data['price_sold']
            data['artwork_description'] = data['artwork_description'].replace("Provenance", "<br><strong>Provenance</strong><br>")
            data['artwork_description'] = data['artwork_description'].replace("Literature", "<br><strong>Literature</strong><br>")
            data['artwork_description'] = data['artwork_description'].replace("Exhibited", "<br><strong>Exhibited</strong><br>")
            data['artwork_description'] = data['artwork_description'].replace("Exposition", "<br><strong>Expositions</strong><br>")
            data['artwork_description'] = data['artwork_description'].replace("Bibliographie", "<br><strong>Literature</strong><br>")
            data['artwork_description'] = data['artwork_description'].replace("Condition report", "<br><strong>Condition Report</strong><br>")
            data['artwork_description'] = data['artwork_description'].replace("Notes:", "<br><strong>Notes:</strong><br>")
            data['artwork_description'] = "<strong><br>Description<br></strong>" + data['artwork_description']
            data['artwork_description'] = data['artwork_description'].replace('"', "'").replace(",",".")
            if 'artwork_size_notes' in data.keys():
                sizeparts = data['artwork_size_notes'].split("x")
                print(sizeparts)
                if sizeparts.__len__() > 0:
                    data['artwork_measurements_height'] = sizeparts[0]
                    mups = re.search(measureunitPattern, data['artwork_measurements_height'])
                    if mups:
                        data['auction_measureunitPattern'] = mups.groups()[0]
                        data['artwork_measurements_height'] = measureunitPattern.sub("", data['artwork_measurements_height'])
                if sizeparts.__len__() > 1:
                    data['artwork_measurements_width'] = sizeparts[1]
                    mups = re.search(measureunitPattern, data['artwork_measurements_width'])
                    if mups:
                        data['auction_measureunitPattern'] = mups.groups()[0]
                        data['artwork_measurements_width'] = measureunitPattern.sub("", data['artwork_measurements_width'])
                        data['artwork_measurements_width']="".join(re.findall("((?:\d+(?:\.\d*)?|\.\d+))",data['artwork_measurements_width']))
                        print(data['artwork_measurements_width'])
                        print("++++++++++++++++++")
                if sizeparts.__len__() > 2:
                    data['artwork_measurements_depth'] = sizeparts[2]
                    mups = re.search(measureunitPattern, data['artwork_measurements_depth'])
                    if mups:
                        data['auction_measureunitPattern'] = mups.groups()[0]
                        data['artwork_measurements_depth'] = measureunitPattern.sub("", data['artwork_measurements_depth'])
                
                
            if 'price_sold' not in data.keys() or data['price_sold'] == "":
                data['price_sold'] = ""
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
                beginspacePattern = re.compile("^\s+")
                endspacePattern = re.compile("\s+$")
                materials = data['artwork_materials']
                materialparts = materials.split(" ")
                catfound = 0
                for matpart in materialparts:
                    #print(matpart)
                    if matpart in ['in', 'on', 'of', 'the', 'from']:
                        continue
                    try:
                        matPattern = re.compile(matpart, re.IGNORECASE|re.DOTALL)
                        for enkey in matcatdict_en.keys():
                            if re.search(matPattern, enkey):
                                data['artwork_category'] = matcatdict_en[enkey].replace(",",".")
                                if data['artwork_category'] == "material_category":
                                    data['artwork_category'] = "Unknown"
                                catfound = 1
                                break
                        for frkey in matcatdict_fr.keys():
                            if re.search(matPattern, frkey):
                                data['artwork_category'] = matcatdict_fr[frkey].replace(",",".")
                                if data['artwork_category'] == "material_category":
                                    data['artwork_category'] = "Unknown"
                                catfound = 1
                                break
                        if catfound:
                            break
                    except:
                        pass
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
    pageurl = "http://216.137.189.57:8080/scrapers/finish/?scrapername=Desa&auctionnumber=%s&auctionurl=%s&scrapertype=2"%(auctionno, urllib.parse.quote(auctionurl))
    pageResponse = None
    try:
        pageResponse = urllib.request.urlopen(pageurl)
    except:
        print ("Error: %s"%sys.exc_info()[1].__str__())  




if __name__ == "__main__":
    if sys.argv.__len__() < 5:
        print("Insufficient parameters")
        
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
    desa = DesaBot(auctionurl, auctionnumber)
    fp = open(csvpath, "w")
    fieldnames = ['auction_house_name', 'auction_location', 'auction_num', 'auction_start_date', 'auction_end_date', 'auction_name', 'lot_num', 'sublot_num', 'price_kind', 'price_estimate_min', 'price_estimate_max', 'price_sold', 'artist_name', 'artist_birth', 'artist_death', 'artist_nationality', 'artwork_name', 'artwork_year_identifier', 'artwork_start_year', 'artwork_end_year', 'artwork_materials', 'artwork_category', 'artwork_markings', 'artwork_edition', 'artwork_description', 'artwork_measurements_height', 'artwork_measurements_width', 'artwork_measurements_depth', 'artwork_size_notes', 'auction_measureunit', 'artwork_condition_in', 'artwork_provenance', 'artwork_exhibited', 'artwork_literature', 'artwork_images1', 'artwork_images2', 'artwork_images3', 'artwork_images4', 'artwork_images5', 'image1_name', 'image2_name', 'image3_name', 'image4_name', 'image5_name', 'lot_origin_url']
    fieldsstr = ",".join(fieldnames)
    fp.write(fieldsstr + "\n")
    page = 1
    lastlotstartnum = 0
    while True:
        soup = BeautifulSoup(desa.currentPageContent, features="html.parser")
        lotsdata = desa.getLotsFromPage()
        if lotsdata.__len__() == 0:
            break
        info = desa.getInfoFromLotsData(lotsdata, imagepath, downloadimages)
        if info.__len__() > 0:
            lotstartnum = info[0]['lot_num']
            if int(lotstartnum) == int(lastlotstartnum):
                break
            lastlotstartnum = lotstartnum
        for d in info:
            for f in fieldnames:
                if f in d and d[f] is not None:
                    fp.write('"' + str(d[f]) + '",')
                else:
                    fp.write('"",')
            fp.write("\n")
        page += 1
        if 'bid.' in desa.baseUrl:
            nextpageurl = auctionurl + "?page=%s&limit=36"%page
            print("Next page url: %s"%nextpageurl)
            desa.currentPageContent = desa.getNextPage(nextpageurl)
        else:
            break
    fp.close()
    updatestatus(auctionnumber, auctionurl)

# Example: python desa.py "https://bid.desa.pl/auctions/1-616J0U/sztuka-wspczesna-klasycy-awangardy-po-1945"   1126ASW106   /Users/saiswarupsahu/freelanceprojectchetan/desa_1126ASW106.csv  /Users/saiswarupsahu/freelanceprojectchetan/1-5TNCV9 0 0

