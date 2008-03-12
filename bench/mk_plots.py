#
# Author: Pearu Peterson
# Created: February 2008
#

import os
import sys
import glob
import time

target_dir = 'html' # where the .html and .png files are created
files = glob.glob('results/*/*/test_*.py')
files.sort(reverse=True)

if not os.path.isdir(target_dir):
    os.mkdir(target_dir)

benchmarks = {}
titles = {}
hashes = {}
for fn in files:
    b = os.path.basename(fn)
    platform = os.path.basename(os.path.dirname(os.path.dirname(fn)))
    r = int(os.path.basename(os.path.dirname(fn)))
    if 0 and b=='test_rational.py' and r in [566,567]:
        print 'Skipping',fn
        continue
    
    if b not in benchmarks:
        benchmarks[b] = {}
    platform_d = benchmarks[b]

    if platform not in platform_d:
        platform_d[platform] = {}
    d = platform_d[platform]

    f = open(fn,'r')
    content = f.read()
    f.close()
    ns = {}
    exec content in ns, ns
    stones = ns.get('STONES')
    if stones is None:
        print 'Removing broken', fn
        os.remove(fn)
        continue
    h = ns.get('HASH')
    if h is None:
        print 'Missing hash, need to recompute', fn
        continue
    if b not in hashes:
        hashes[b] = h
    else:
        if h!=hashes[b]:
            print 'Different hashes, need to recompute', fn
            continue
    d[r] = stones
    if b not in titles:
        titles[b] = ns['TITLE']

def create_figure(testcase, target_dir='.'):
    import pylab
    from matplotlib.font_manager import FontProperties
    print 'Processing',testcase
    title = titles.get(testcase)
    if title is None:
        return
    platforms = sorted(benchmarks[testcase].keys())
    mx_revision = 0
    mn_revision = 10000000
    if isinstance(title, str):
        title = [title]

    platform_data = []
    for platform in platforms:
        data = benchmarks[testcase].get(platform)
        if data is None or not data: continue
        revisions, stones = zip(*sorted(data.items()))
        mx_revision = max(mx_revision, revisions[-1])
        mn_revision = min(mn_revision, revisions[0])
        platform_data.append((platform, revisions, stones))
    
    for j in range(3):
        if j:
            fig = pylab.figure(figsize=((9+4*j), (4+2*j)*len(platforms)))
        else:
            fig = pylab.figure(figsize=((6), (3)*len(platforms)))
        i = 0
        for platform, revisions, stones in platform_data:
            i += 1
            pylab.subplot(len(platform_data),1,i)
            pylab.title('%s: %s' % (testcase, platform))
            if j or i==len(platform_data):
                pylab.xlabel('revisions')
            pylab.ylabel('stones')
            if j:
                pylab.plot(revisions[-100:], stones[-100:],'-x')
            else:
                #pylab.semilogy(revisions, stones)
                pylab.plot(revisions, stones)
            pylab.grid()
            if j:
                k = revisions[-100:][0]
            else:
                k = mn_revision
            while k%10: k -= 1
            if len(revisions)>50 and j>1:
                pylab.setp(pylab.gca(), 'xticks', range(k,mx_revision+10, 10))
            pylab.setp(pylab.gca(), 'xlim', [k, 10*(1+mx_revision//10)])
            if isinstance(stones[-1], (list,tuple)) and j:
                pylab.setp(pylab.gca(), 'ylim', [min(stones[-1])//2, max(stones[-1])*1.5])
            if j==1:
                pylab.legend(title, loc=3, prop=FontProperties(size='smaller'))
        fn = os.path.join(target_dir,'%s_%s.png' % (testcase, j))
        print 'Saving plot to',fn
        fig.savefig(fn)

    fn = os.path.join(target_dir,testcase + '.html')
    print 'Creating',fn
    f = open(fn, 'w')
    print >> f,'<head></head><body>'
    print >> f,'<h1>Details of the %s benchmark</h1>' % (testcase)
    print >> f,'<p><a href="index.html">Back to main page</a></p>'
    print >> f,'<p>The stones of the last 100 revisions are shown.</p>'
    print >> f,'<p><a title="Click image to see it without a legend" href="%s"><img src="%s"></a></p>' % (testcase+'_2.png',testcase+'_1.png')
    print >> f,'<table border="1" align="center">'
    print >> f,'<caption>Table of <a href="http://mpmath.googlecode.com/svn/trunk/bench/%s">mpmath/bench/%s</a> stones</caption>'\
          % (testcase, testcase)
    print >> f,'<tr><th>Revision<th>' + '<th>'.join(platforms)
    for revision in range(mx_revision, mn_revision-1, -1):
        stones = []
        for p in platforms:
            stones.append('%s' % (benchmarks[testcase][p].get(revision,'')))
        rev_link = '<a href=http://code.google.com/p/mpmath/source/detail?r=%(revision)s>%(revision)s</a>' % dict(revision=revision)
        print >> f,'<tr><td>'+rev_link+'<td>'+'<td>'.join(stones)
    print >> f,'</table></body>'
    f.close()


f=open(os.path.join(target_dir, 'index.html'), 'w')
print >> f,'<head></head><body>'

print >> f,'''
<h1>Main page of <a href="http://mpmath.googlecode.com/">mpmath</a> benchmarks</h1>

<p>Last update: <tt>%s</tt></p>
<p>These results are generated using scripts from
<a href="http://mpmath.googlecode.com/svn/bench/">bench/</a>
developed by Pearu Peterson.
</p>

<h2>Definitions</h2>
<p>
<dl>
<dt><em>stones</em>
<dd>A ratio of the <em>benchmark timing</em> and the <em>base timing</em> result. Less <em>stones</em> are better.
<dt><em>base timing</em>
<dd>The result of  <tt>Timer("foo()", "def foo(): pass").timeit(number)/number</tt>.
</dl>
</p>

<h2>Results</h2>

<h3>Shortcuts to details pages</h3>

<p>
''' % (time.asctime())

for k in sorted(benchmarks):
    j = len(benchmarks[k])
    print >> f,'<a href="%s">%s</a><br>' % (k+'.html', k)

print >> f,'''
</p>

<h3>Overall graphs</h3>
'''

for k in sorted(benchmarks):
    j = len(benchmarks[k])
    print >> f,'<p><a href="%s"><img src="%s"><br>Show details of the %s benchmark</a></p>'\
          % (k+'.html', k+'_0.png', k)
    #print >> f,'<p><a href="%s"><img height="%s" src="%s"><br>Show details of the %s benchmark</a></p>'\
    #      % (k+'.html',300*j, k+'_0.png', k)
    create_figure(k, target_dir)

print >> f,'</table></body>'
f.close()
