
git clone https://github.com/blackhawk70/blackhawk70.github.io.git
cd blackhawk70.github.io
cp index.html ../index.html
git config user.email "atounsi@stevens.edu"
git config user.name "blackhawk707070"
git filter-branch --index-filter 'git rm --cached --ignore-unmatch *.html' -- --all
rm -Rf .git/refs/original
rm -Rf .git/logs/
git gc --aggressive --prune=now
mv ../index.html .
git add index.html
git commit -m "clean cache"
git push -f https://blackhawk70:ghp_BJ3YUpOv@github.com/blackhawk70/blackhawk70.github.io.git --all
cd ..
rm -rf blackhawk70.github.io/
