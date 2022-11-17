# AdiBags Creator (by Zottelchen)

**What does it do?**

It takes item IDs from lists in /items and creates an AdiBags Plugin from that. Just put your Blizzard API credentials into system variables BLIZZ_ID and BLIZZ_SECRET and run create.py.

The ID lists may contain some special symbols:

* \# - defines a comment for the generated Markdown file
* ! - defines a description for the AdiBags filter
* $ - defines a hex color for the AdiBags category
* \* - defines an override method to check against
* & - defines an additional method to check in addition to item ID (needs to return false)