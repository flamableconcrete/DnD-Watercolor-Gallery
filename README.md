# DnD-Watercolor-Gallery
Code for a website to display D&D watercolor stains used for homebrew material.

[View the site here](https://watercolors.giantsoup.com)! 

## Description of files
Here is a quick overview of a few files in the repository:

* `albums` directory - `.gitignore`'d directory of original artwork that I create using GIMP.
* [my-sigal-theme/](my-sigal-theme/) - modified version of the [colorbox](https://github.com/saimn/sigal/tree/master/sigal/themes/colorbox) theme from [sigal](https://github.com/saimn/sigal).
The only real difference is adding `background: #000;` to `style.css` and `colorbox.css` so the background appears black instead of white.
* [run.py](run.py) - Has several commands to help manage the website and back-end data.
  * `do-backup` - Zips the local `albums` directory and uploads it to Digitalocean Spaces.
  * `do-download` - Used in Travis CI to download and unzip the file of original artwork from Digitalocean Spaces.
  * `sigal-build` - Wrapper for `sigal build`.
  * `sigal-compress` - Compress the images without doing a full `sigal build`.
  * `azure-backup-website` - Backup the current website to an alternate Azure container.
  * `azure-deploy` - Upload the _build directory to Azure.
* [utils.py](utils.py) - The bulk of the logic that powers the commands in `run.py`.
* [DirectoryClient.py](DirectoryClient.py) - A client for easier streamlined use for Azure Storage Blobs.

## Build site locally
If you want to build this locally, it is fairly straightforward, although you will need a local `albums` directory with any number of .png files in it.

```shell script
pip install -r requirements.txt

# this takes a few minutes as it converts all the images for the final step
# it creates a local _build directory with these files
sigal build

sigal serve
```

Then open http://127.0.0.1:8000 in a browser and you should be good to go!

## Hosting notes
Here is the path I went down trying to find a place to host this blasted website.
Mostly this is an issue with where to host and reference the raw images.
At present (Sept 2020), there are ~300 images that are a combined ~250 MB.

* Keep everything in GitHub and use Git LFS
  * Pros: Very neat organizational structure, keep everything in one place, free up to 1 GB storage, 1 GB bandwidth/month.
  * Cons: Using Travis CI to pull the whole repo uses 25% of the free bandwidth for the month on each git push, which could grow over time.
* Amazon S3 (NOTE: I did not actually consider this or research it)
  * Pros: Reliable, maybe cheap
  * Cons: I'm intimidated by the AWS overall environment and not convinced I won't get charged $10,000 because of my stupidity
* Digital Ocean Spaces
  * Pros: Reliable, Cheap ($5/month) for 250 GB storage, 1 TB bandwidth/month, S3 compatible API
  * Cons: After writing up and testing some scripts found that it can not host static websites (easily? at all?)
* Azure Static Web Apps Preview
  * Pros: Dedicated to hosting static web apps, uses GitHub Actions (neat! made me learn new syntax!)
  * Cons: Confusing architecture, couldn't easily figure out how it was using Oryx to successfully build the sigal site
* Azure Blob Storage
  * Pros: Cheap (structured pricing like AWS), reliable, can host static websites!
  * Cons: Also intimidating like AWS (but I'm sticking with it so far)


