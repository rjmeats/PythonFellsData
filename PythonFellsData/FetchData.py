from urllib.request import urlopen
from bs4 import BeautifulSoup
import re
import time
import csv

URLBase = "https://en.wikipedia.org"

# Pattern of Latitude / Longitude values in detailed fell pages. E.g. 54°28′55.2″N
# In most cases, the seconds are whole numbers, but a couple include decimals
pLatLong = re.compile(r"([0-9]?[0-9]?[0-9])°([0-9]?[0-9])′([0-9]?[0-9]\.?[0-9]*)″([NSEW])")
# Convert latitude or longitude in degrees-minutes-seconds to signed degrees using decimals rather than minutes and seconds
def degreeToDecimal(dms) :
    matchLatLong = pLatLong.match(dms)
    if matchLatLong :
        value = float(matchLatLong.group(1)) + float(matchLatLong.group(2))/60 + float(matchLatLong.group(3))/60/60
        # Indicate South and West values as negative
        if matchLatLong.group(4) in ['S', 'W'] :
            value *= -1
    else :
        # Special value to show we didn't match the pattern
        value = 999
    return round(value, 4)

# Method to read the Wikipedia page for a specific fell, extract the latitude and longitude values from the page and return
# them as a tuple
def getLocationDummy(fellInfo) :
    print(fellInfo["name"])
    return ("54.32", "-3.045")

def getLocation(fellInfo) :
    print(fellInfo["name"])
    # Keep the requests to a slow rate
    time.sleep(1)

    # Fetch the detail page
    fellDetailURL = URLBase + "/" + fellInfo["wikihref"]
    fellDetailHTML = urlopen(fellDetailURL)
    detailBsObj = BeautifulSoup(fellDetailHTML, features="html.parser")

    # Find the class="latitude" and class="longitude span elements within the web page - their text provides lat and long strings. E.g.
    #    ... <span class="latitude">54°28′55.2″N</span> <span class="longitude">3°13′8.4″W</span> ...
    latitude = detailBsObj.find(attrs={"class" : "latitude"})
    longitude = detailBsObj.find(attrs={"class" : "longitude"})
    # Convert to decimal form rather than using minutes and seconds
    lat = degreeToDecimal(latitude.get_text())
    long = degreeToDecimal(longitude.get_text())

    # If the return value is 999, there was a problem with the values
    if(lat == 999) :
        print("Failed to match latitude string : [", latitude.get_text(), "] for fell ", fellInfo["name"])
    if(long == 999) :
        print("Failed to match longitude string : [", longitude.get_text(), "] for fell ", fellInfo["name"])

    return (lat, long)

#
# Main program
#

# Read the main Wikipedia page listing Lakeland fells (as defined by Alfred Wainwright's 7 books) and pass to
# the Beautiful Soup parser
mainURL = URLBase + "/" + "wiki/List_of_Wainwrights"
mainHTML = urlopen(mainURL)
BsObj = BeautifulSoup(mainHTML, features="html.parser")

# Regular expressions used against text extracted from the web page.
# Book name pattern, e.g Book Two: The Far Eastern Fells, extracting book number and region
pBook = re.compile(r"(Book\s+(.*):\s+The\s+(.*)\s+Fells).*")
# Fell name pattern, e.g. Stybarrow Dodd, 843 m (2,766 ft), extracting fell name, height in metres and height in feet.
# Note that the spaces in the text are actually #160s, so must use \s to match
pFell = re.compile(r"(.*), (\d+)\s+m \(([0-9,]*)\s+ft\)")

# Dictionary to convert book numbers as words into corresponding integers
bookNos = { "One" : 1, "Two" : 2, "Three" :3, "Four" : 4, "Five" : 5, "Six" : 6, "Seven" : 7}

# Find the book heading elements and the lists of fells interspersed for each book
nodes = BsObj.findAll(["h3", "li"])

# 
fellCount=0
fellLimit=1000      # 214 in total, used for looking at small numbers during development
fells = []

# Look at each book/fell node, pull data out and create a list of fells
for node in nodes :
    # Option to stop early for use during development
    if fellCount == fellLimit :
        break
    # See whether the node text matches the book or fell pattern
    t = node.get_text()
    mBook = pBook.match(t)
    if mBook :
        # We've reached a new book heading, record its details
        currentBook=mBook.group(1)
        bookNo=mBook.group(2)
        fellsGroup=mBook.group(3)
    else :
        mFell = pFell.match(t)
        if mFell :
            # We've found another fell in the list for a specific book, record its details
            #if mFell.group(1) != "Great Gable" :
            #    continue
            fellCount += 1
            # The URL for the detail page is available via the link part of the node, e.g.
            #  <li><a href="/wiki/Stybarrow_Dodd" title="Stybarrow Dodd">Stybarrow Dodd</a>...<li>
            wikihref=node.find("a")["href"]
            # Set up a dictionary of attributes for this fell, pulling out name and height info from the pattern match, and adding in the book info
            fell = { "name":mFell.group(1), "heightm":int(mFell.group(2).replace(",", "")), "heightft":int(mFell.group(3).replace(",", "")), "wikihref":wikihref, 
                     "book":currentBook, "bookno":bookNos[bookNo], "fellsgroup":fellsGroup }
            # Fetch the latitude and longitude from the detailed page for the fell, and add to the dictionary
            location = getLocation(fell)
            fell["latitude"] = location[0]
            fell["longitude"] = location[1]

            fells.append(fell)

print()
print("Found", len(fells), "fells")
print()
print("Example fells:")
print()
for fell in fells[0:10] :
    print(fell)

# List fells where we had a problem producing a latitude/longitude value
print()
for fell in fells :
    if fell["latitude"] == 999 or fell["longitude"] == 999 :
        print("*** Failed to extract location of fell", fell["name"])

# Write out the fells into a CSV file, using the Python csv package to help
CSVFilename = "data/lakelandfells.csv"
with open(CSVFilename, "w", newline="") as csvfile:
    myCSVWriter = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    myCSVWriter.writerow(["Name", "Height (m)", "Height (ft)", "Fell group", "Latitude", "Longitude"])
    for fell in fells :
        myCSVWriter.writerow([fell["name"], fell["heightm"], fell["heightft"], fell["fellsgroup"], fell["latitude"], fell["longitude"] ])

print()
print("Fells data written to csv file:", CSVFilename)

