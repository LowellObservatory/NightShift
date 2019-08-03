# NightShift

[![Codacy Badge](https://api.codacy.com/project/badge/Grade/15ad20635f74475a9e16b219894b483a)](https://app.codacy.com/app/astrobokonon/NightShift?utm_source=github.com&utm_medium=referral&utm_content=LowellObservatory/NightShift&utm_campaign=Badge_Grade_Dashboard)

A collection of modules to be used in at least NightWatch, and probably
many/most other projects that are in the hopper at the moment.

## History

Many/most of these modules grew out of the [Camelot](https://www.github.com/LowellObservatory/Camelot) 
repository, where they were born.  I moved the code over via a copy rather than a fork because 
I felt these are distinct enough projects, and Camelot contains basically a random assortment 
of stuff.  There are many old (closed) issues and a ton of commits over in Camelot that
might be of interest.

## Installation

To develop and use at the same time:
(in the source directory)

```bash
pip install -e .
```

This is needed because I've used ```package_data``` to simplify references
to static resources (like error images, fonts, etc.).
