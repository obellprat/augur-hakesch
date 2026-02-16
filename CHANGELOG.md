## 1.1.0 (2026-02-16)

### Feat

- **frontend**: added technical documentation
- **frontend**: Session tracking
- **frontend**: Added analytics (umami)
- **calibration**: Set physical calibration values back to default
- **frontend**: vo_20 and psi validation with error message
- **frontend,-precipitation**: Change chart library and show uncertainity
- **external-monitoring**: new tool for external monitoring service
- **backend,-frontend**: monitoring page and statistics
- **frontend**: included the Arbeitshilfe
- **frontend**: added geotools suter and bellprat climate consulting under the credits. and a link to github
- **frontend,-precipitation**: Autocomplete location box, share link
- **frontend,-precipitation**: get data from db, adjust graph and css style fixes
- **frontend**: Table style vo_20 and psi entry
- **frontend**: Translation fix and new language french

### Fix

- **frontend**: small layout fixes and text changes
- **frontend**: description of Abflussprozesstypen changed
- **frontend**: jährlich not jährig
- **api,-nam**: calibrated nam cn lookup table
- **api**: not so aggressive monitorin, so the cpu remains stable
- **frontend,-api**: updated zone_parameters with calibrated values
- **frontend**: bigger map for projects (creating and editing)
- **frontend**: Rounding the results to one decimal place
- **frontend**: Moving the Save and Calculate button
- **frontend**: Hades values without decimal places. Move the button

### Refactor

- cleanup and better description in readme

## 1.0.0 (2025-12-15)

### Feat

- **frontend**: NAM calibration of storm event
- **frontend**: ClarkWSL Help modal
- **frontend**: Infobutton with hoover for explanations
- **frontend**: Show a progressbar while calculation
- **frontend**: When creating a project, the user is asked whether the geodata should be calculated
- **frontend**: Delete multiple projects simultaneously
- **frontend**: Reorganization of the Hydrological Calculation Page. All fields below each other and new layout
- **api,frontend**: New recurrence periods added (30, 100, 300)
- **api,frontend**: User can get the HADES data in the frontend. Takes the values from the provided netcdf file
- **frontend,api**: Update to clima scenarios of meteoschweiz
- **calibration**: Integrate results of the first calibration in the methods
- **Science**: Add science page, change light background, add marker to precipitation tool
- **api**: faster catchment calculations
- **frontend,-api**: NAM hydrograph implementation
- **frontend**: Combine annualities and init hydrological processes
- **darkmode-images**: Add functionality to show different images in dark mode as well as the logos
- **api,frontend**: User can upload his own soil type shapefile
- **api**: Possibility to add custom soil shapefile to calculate cn
- **frontend**: NAM integration into the frontend
- **api**: Use the Bodeneignungskarte in Switzerland to generate the curve numbers
- **frontend**: shows a spinner when loading data from database
- **frontend,api**: integration of clark-wsl calculation
- **frontend**: Display the geodata in project overview
- **frontend**: Show the calculated river network
- **api,frontend**: integrating version display in frontend and backend
- **frontend**: Show results as Plots
- **frontend**: Show results as Plots
- **frontend**: Show results as Plots

### Fix

- **frontend**: Remove the buttons for calculation and saving on the top right
- **frontend**: InvalidateAll on project overview after recalculation shows also the geo-metadatas
- **frontend**: reload branches over the isozones after catchment analysis
- **frontend**: HADES values with correct coordinate transformation
- **frontend**: csrf disabled because multiple subdomains (www and without)
- **frontend**: checks the precip values before the calculation
- **frontend**: error handling when api is not working
- **frontend**: faster project loading without the geojsons
- **frontend**: Text adjustments for recurring periods
- **frontend**: layout improvements on calculation page
- **API,-NAM**: bug fixing cc_factor on rain in NAM
- **api,ClarkWSL**: bugfixing fraction lists missing items. It is a list
- **ClarkWSL**: Ensure that discharge types are handed over as strings
- **interpolation-koella**: Koella was not correctly passed for the loglog-interpolation without explicitly putting x=20 and x=100
- **api**: Fix for Koella's calculation with the new recurrence periods
- **koella**: Further add tolerance for TB conversion
- **koella**: Change parameters for TB conversion also in the second koella function
- **loglog-int**: fix isclose issue in function
- **loglog-int**: Log-log interpolation is not selecting properly 300 year period
- **koella**: Correct TB conversion parameters
- **frontend**: sort results by annuality
- **climate-change-signal**: values were wrong and have adjusted according to new "note for estimating future changes in extreme precipitation return levels" from MeteoSwiss
- **api**: fixes strange bug with pysheds array with sizes of 160000... make the reading window a little bit smaller
- **TB-convergence**: Adjust parameters for TB convergence in MF and Koella to avoid failing convergence
- **frontend**: welcome text change
- **frontend**: same height for all card-img-top
- **frontend**: fixes bugs in adding new calculations after saving
- **api**: Use a_crit 1000 and not 10000 for generating isozones
- **api,frontend**: Better error description, when the calculation is not working
- **api**: Use the correct cumulative length for the calculation and not the maximum length
- **frontend**: Calculations cannot be performed if the geodata has not yet been calculated. The user will be informed of this. Fix #41
- **frontend**: The data for the calculations is saved before the calculations are performed
- **api**: change cumulative flow length in project-wide calculation
- **api**: send the Cumulative channel length in km and not in m
- **Additional-changes-to-Fliesszeitverfahren-and-Kölla**: Calculation corrections
- **discharge.py**: calculation corrections for koella and clark-wsl
- **frontend**: after saving calculation-data it was not possible to add other calculations. And fixes the decimal places bug
- **api,frontend**: Enable to download isozone, catchment and branches as tif and geojson
- **api,frontend**: Calculation progress display fix
- **frontend**: Displays an error message if there was an exception in the API functions
- **frontend**: Frontend starts even the backend is not accessible
- bump version files
- **frontend**: show version in frontend

### Refactor

- **frontend**: Set and hide standard NAM parameters
- **frontend**: hide donation box
- **api,frontend**: small changes in spinner, translation and docker
- **api**: delete unused api calculation files
- **Change-the-versioning-system-to-Commitizen**: Previously, semantic versioning was used. Commitizen is more widely used

## 0.2.0 (2025-07-25)

### Feat

- **frontend**: integrated discharge project navigation into main navigation
- **frontend**: Translation
- **frontend, api**: Koella calculation
- **frontend**: delete hydro calculations
- **frontend**: delete hydro calculations
- **api,frontend**: Implementation of Mod Fliesszeitverfahren
- **frontend**: geodata page and creation for hakesch 2 projects
- **api**: prisma integration in fastapi
- **frontend**: Prisma and HAKESCH2 project view
- **api**: updated isozones calculation
- **api**: authentification with keycloak
- **frontend**: User Page with api token
- **frontend**: New Augur frontend
- **frontend**: New Augur frontend
- **frontend**: New Augur frontend
- **api**: implementing isozonation
- **api**: isozones calculation
- **api**: show version in docs
- add automatic versioning

### Fix

- **api**: create all data directories
- add creation of dirs in Taskfile for downloading data
