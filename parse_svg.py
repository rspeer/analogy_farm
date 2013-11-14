from BeautifulSoup import BeautifulStoneSoup
import json

data = open('solved.svg').read()
svg = BeautifulStoneSoup(data)

text_nodes = svg.g.findChildren('text')
text_items = []

for node in text_nodes:
    # translate: 1160.7857,544.70923
    x = float(node['x']) + 1160.7857
    y = float(node['y']) + 544.70923
    item = (y, x, node.text)
    text_items.append(item)

text_items.sort()

outfile1 = open('boxes.js', 'w')
print >> outfile1, "$(function () { $('body').append("

for counter, item in enumerate(text_items):
    print >> outfile1, '\ttextbox(%d, %d, %d),' % (item[1], item[0], counter)

print >> outfile1, "); });"
outfile1.close()

labeled = [item[2] for item in text_items]
outfile2 = open('boxes.json', 'w')
json.dump(labeled, outfile2, indent=2)
outfile2.close()
