var GeoSearchControl = window.GeoSearch.GeoSearchControl;
var OpenStreetMapProvider = window.GeoSearch.OpenStreetMapProvider;

let map;
let augurLayer;
let currentFocus;
let locationData;
let latlong;
let tilesPeriod = 10;
let defaultYear = 2030;
let uncertainty = false;

// setup
const provider = new OpenStreetMapProvider();
const locationIcon = new L.icon({
  iconUrl: 'assets/images/tools/location_pin.svg',
  shadowUrl: 'assets/images/tools/location_pin_shadow.svg',

  iconSize: [48, 48], // size of the icon
  shadowSize: [48, 48], // size of the shadow
  iconAnchor: [24, 48], // point of the icon which will correspond to marker's location
  shadowAnchor: [24, 48], // the same for the shadow
  popupAnchor: [24, 0], // point from which the popup should open relative to the iconAnchor
});
const marker = new L.marker([0, 0], { icon: locationIcon });


async function init() {
  document.addEventListener('DOMContentLoaded', function () {
    //navigateToCurrentURL();
  });

  window.addEventListener('popstate', (event) => {
    let stateObj = { pageKey: event.state.pageKey };
    buildPage(stateObj, false);
  });

  // configure tile laye
  let baseLayer = L.tileLayer('https://tiles.stadiamaps.com/tiles/stamen_toner_lite/{z}/{x}/{y}{r}.png', {
	attribution: 'Map tiles by <a href="http://augur.world">AUGUR</a> and &copy; <a href="https://www.stadiamaps.com/" target="_blank">Stadia Maps</a> &copy; <a href="https://www.stamen.com/" target="_blank">Stamen Design</a> &copy; <a href="https://openmaptiles.org/" target="_blank">OpenMapTiles</a> &copy; <a href="https://www.openstreetmap.org/about/" target="_blank">OpenStreetMap contributors</a>',
	subdomains: 'abcd',
	minZoom: 0,
	maxZoom: 20,
	opacity: 0.5,
	ext: 'png'
 });

// let baseLayer = L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
 	//attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
	//subdomains: 'abcd',
//	maxZoom: 20,
//	opacity: 0.5
//  });


  if (Boolean(location.search) && location.search.includes('period')) {
    const period = (new URLSearchParams(location.search)).get('period');
    if (['10', '20', '30', '100'].includes(period)) tilesPeriod = period;
    document.querySelector("select[name=tiles_period]").value = tilesPeriod;
  }

  // https://obellprat.github.io/tilesaugur/tiles${tilesPeriod}/{z}/{x}/{-y}.png 
  augurLayer = L.tileLayer(`https://augur.world/tilesaugur/tiles${tilesPeriod}/{z}/{x}/{y}.png`, {
    detectRetina: true,
    opacity: 1,
  });
 
  // create map
  map = new L.map('map__contents__tiles', {
    center: new L.LatLng(0, 0),
    zoom: 4,
    minZoom: 4,
    maxZoom: 9,
    zoomControl: false,
    // maxBounds: L.latLngBounds(L.latLng(50, -74.227), L.latLng(40.774, -74.125)),
    maxBounds: [
      [-50, -Infinity],
      [50, Infinity],
    ],
    layers: [augurLayer,baseLayer],
  });
  
  if (Boolean(location.search) && location.search.includes('lat') && location.search.includes('lng')) {
    const lat = (new URLSearchParams(location.search)).get('lat');
    const lng = (new URLSearchParams(location.search)).get('lng');
    if (location.search.includes('year')) {
      const year = (new URLSearchParams(location.search)).get('year');
      if (['2030', '2050', '2090'].includes(year))  defaultYear = year;
    }
    setLocation([lat, lng], defaultYear);
  }

  // add event listeners
  // selecting location (use long press for touch devices)
  if (is_touch_enabled()) map.addEventListener('contextmenu', (event) => setLocation([event.latlng?.lat, event?.latlng?.lng]));
  else map.addEventListener('click', (event) => setLocation([event.latlng?.lat, event?.latlng?.lng]));

  //let menuBtn = document.getElementById('map__contents__navigate__menu-toggle');
  //menuBtn.addEventListener('click', toggleAside);

  //let closeMenuBtn = document.getElementById('map__close');
  //closeMenuBtn.addEventListener('click', toggleAside.bind('close'));

  let asideHeaderButtons = document.querySelectorAll('#aside header nav a');
  for (let link of asideHeaderButtons) link.addEventListener('click', onClickPageLink);

  const clearLocationBtn = document.querySelector('#map__contents__navigate__search .icon[alt="Clear"]');
  clearLocationBtn.addEventListener('click', clearLocation);

  const detailsHandler = document.querySelector('#map__contents__details__drag-handle');
  detailsHandler.addEventListener('click', handleDetailsPosition);

  const periodHandler = document.getElementById('map__contents__period');
  periodHandler.addEventListener('change', handlePeriodValue);

  const shareHandler = document.querySelector('button[name=share]');
  shareHandler.addEventListener('click', handleShareClick);

  const downloadHandler = document.querySelector("button[name=download]");
  downloadHandler.addEventListener("click", download);

  const getLocationHandler = document.querySelector("button#getLocation");
  getLocationHandler.addEventListener("click", getCurrentLocation);

  const climateChangeHandler = document.querySelector('select[name=climate_change_period]');
  climateChangeHandler.value = defaultYear;
  climateChangeHandler.addEventListener('change', handleClimateChange);

  const uncertaintyChangeHandler = document.querySelector('input[name=uncertainty_check]');
  uncertaintyChangeHandler.addEventListener('change', handleUncertainty);

  const findHandler = document.getElementById('map__contents__navigate__search__input');
  findHandler.addEventListener('input', debounce(handleFind.bind(findHandler), 300));
  findHandler.addEventListener('keydown', handleKeyDownFind);

  fallBackLangFile = await languages["en"].source;

  await translatePage();
}

function getCurrentLocation() {
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(getToPosition);
  }
}

async function getToPosition(position) {
  map.flyTo([position.coords.latitude, position.coords.longitude], 5);
  marker.setLatLng([position.coords.latitude, position.coords.longitude]).addTo(map)
  await setLocation([position.coords.latitude, position.coords.longitude]);
}

function handleShareClick (){
  //get current url
  const url = new URL(location.href);
  //create new params pair
  const new_params = new URLSearchParams({"lat": latlong[0], "lng": latlong[1], "period": tilesPeriod, "year": defaultYear});
  const new_url = new URL(`${url.origin}${url.pathname}?${new_params}`);
  var textArea = document.createElement("textarea");

  textArea.style.position = 'fixed';
  textArea.style.top = 0;
  textArea.style.left = 0;

  textArea.value = new_url;

  document.body.appendChild(textArea);
  textArea.focus();
  textArea.select();

  try {
    document.execCommand('copy');
    document.querySelector("label[class=tooltiptext]").style.visibility= "visible";
    setTimeout( function() {
        document.querySelector("label[class=tooltiptext]").style.visibility = "hidden";
    }, 1000);
  } catch (err) {
    console.log('Oops, unable to copy');
  }

  document.body.removeChild(textArea);
}

function handleClimateChange(event) {
  defaultYear = event.target.value;

  const precipitationGraph = drawPrecipitactionGraphDOM(locationData, defaultYear, uncertainty);
  const graphContainer = document.getElementById('map__contents__details__graph');
  graphContainer.replaceChildren(precipitationGraph);
}

function navigateToCurrentURL() {
  let urlSlug = window.location.pathname;
  let pageKey = defaultPage;
  for (let key in pages) if (pages[key].slug === urlSlug) pageKey = key;
  let stateObj = { pageKey: pageKey };
  buildPage(stateObj, false);
}
function closeAllLists(elmnt) {
  const inp = document.getElementById('map__contents__navigate__search__input');
  let x = document.getElementsByClassName("autocomplete-items");
  for (let i = 0; i < x.length; i++) {
    if (elmnt != x[i] && elmnt != inp) {
      x[i].parentNode.removeChild(x[i]);
    }
  }
}

function handleKeyDownFind(e) {
  let x = document.getElementById(this.id + "autocomplete-list");
      if (x) x = x.getElementsByTagName("div");
      if (e.keyCode == 40) {
        currentFocus++;
        addActive(x);
      } else if (e.keyCode == 38) { //up
        currentFocus--;
        addActive(x);
      } else if (e.keyCode == 13) {
        e.preventDefault();
        if (currentFocus > -1) {
          if (x) x[currentFocus].click();
        }
      }
}

function debounce(func, timeout = 300){
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => { func.apply(this, args); }, timeout);
  };
}

function generateFileContent() {

  const years = Object.keys(locationData?.period);
  const periods = Object.keys(locationData?.period[years[0]]?.years);

  const values = periods.map((period) => {

    let res = [`${period}-Year in today: ${locationData?.period[years[0]]?.years[period].present}`]
    res = res.concat(years.map((year, index) => {
      let str = "";
      
      str += `${period}-Year in ${year}: ${locationData?.period[year]?.years[period].climate_change}`;
      return str;
    }));

    return res;
  }).reduce((acc, arr) => {
    return acc.concat(...arr);
  }, []).join("\n");
  
  return `# Data downloaded by augur.world
# Selected coordinates:
lat = ${latlong[0]}, lon = ${latlong[1]}
# Precipitation data
${values}
`;
};

function download() {
  var element = document.createElement('a');

  element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(generateFileContent()));
  element.setAttribute('download', latlong[0] + " - " + latlong[1] + ".txt");

  element.style.display = 'none';
  document.body.appendChild(element);

  element.click();

  document.body.removeChild(element);
}

function addActive(x) {
  if (!x) return false;
  removeActive(x);
  if (currentFocus >= x.length) currentFocus = 0;
  if (currentFocus < 0) currentFocus = (x.length - 1);
  x[currentFocus].classList.add("autocomplete-active");
}

function removeActive(x) {
  for (var i = 0; i < x.length; i++) {
    x[i].classList.remove("autocomplete-active");
  }
}

async function handleFind(event) {
  const arr = await provider.search({ query: event.target.value });
  const inp = this;

  let a, b, i, val = this.value;
  if (!val) { return false;}

  closeAllLists();
  currentFocus = -1;
  
  a = document.createElement("div");
  a.setAttribute("id", this.id + "autocomplete-list");
  a.setAttribute("class", "autocomplete-items");

  this.parentNode.appendChild(a);
  const arrayLength = arr.length > 4 ? 4 : arr.length;
  for (i = 0; i < arrayLength; i++) {
    b = document.createElement("DIV");
    b.innerHTML = "<strong>" + arr[i].label.substr(0, val.length) + "</strong>";
    b.innerHTML += arr[i].label.substr(val.length);
    b.innerHTML += "<input type='hidden' value='" + arr[i].label + "' name='label' />";
    b.innerHTML += `<input type='hidden' value='${arr[i].y}' name='lat' />`;
    b.innerHTML += `<input type='hidden' value='${arr[i].x}' name='lng' />`;

    b.addEventListener("click", async function(e) {
        inp.value = this.querySelector("input[name=label]")?.value;

        const latLng = [this.querySelector("input[name=lat]")?.value, this.querySelector("input[name=lng]")?.value];
        closeAllLists();

        await setLocation(latLng);

    });
    a.appendChild(b);
  }
}

/**
 * handle/select period value
 * @param  {Object} event Event that triggered the function
 */
function handlePeriodValue(event) {
  tilesPeriod = event.target.value;
  augurLayer.setUrl(`https://augur.world/tilesaugur/tiles${tilesPeriod}/{z}/{x}/{y}.png`);
}

/**
 * handle/toggle details position
 * @param  {Object} event Event that triggered the function
 */
function handleDetailsPosition(event) {
  const mapEl = document.getElementById('map');
  mapEl.hasAttribute('data-details-as-sheet') ? delete mapEl.dataset.detailsAsSheet : (mapEl.dataset.detailsAsSheet = '');
}

/**
 * loading the contents of a new page within the aside section
 * @param  {Object} event Event that triggered the function
 */
async function buildPage(stateObj, addToHistory) {
  let pageKey = stateObj.pageKey;
  let page = pages[pageKey];
  document.title = 'Augur | ' + page.title;

  // mark current link as selected
  const navigation = document.querySelector('#aside nav');
  for (let child of navigation.children) delete child.dataset.selected;
  navigation.querySelector(`a[to="${page.slug}"]`).dataset.selected = '';

  // update URL and history

  const language = (new URLSearchParams(location.search)).get('lang');

  if (addToHistory) history.pushState(stateObj, '', page.slug + (language ? "?lang=" + language : ""));

  // load module contents
  const target = document.getElementById('aside__content');
  const module = await page.module;
  const content = await module.default(); // render
  target.replaceChildren(content);
  module.init?.(changeLanguage); // only run if function exists


  const lang = new URLSearchParams(location.search).get('lang');

  if (lang && lang !== 'null') {
    document.querySelectorAll(".languages-inputes-container input").forEach(el => {
      if(el.value === lang) {
        el.setAttribute("checked", "checked");
      } else {
        el.removeAttribute("checked");
      }
    });

  }
  await translatePage();
}

function changeLanguage() {
  document.querySelector(".languages-inputes-container").addEventListener("click", (event) => {
    event.stopPropagation();
    event.preventDefault();

    let inputEl = null;

    if (event.target.nodeName === 'LABEL') {
      inputEl = event.target.querySelector("input");
    } else if (event.target.nodeName === "INPUT") {
      inputEl = event.target;
    }

    if (inputEl) {

      document.querySelectorAll(".languages-inputes-container input").forEach(el => {
        el.removeAttribute("checked");
      });

      inputEl.setAttribute("checked", "checked");
      const url = new URL(location);

      url.searchParams.set("lang", inputEl?.value);


      document.location.href = url; 
    }
  })
}

/**
 * prevent default link behaviour and trigger page loading
 * @param  {Event} event Event that triggered the function
 */
function onClickPageLink(event) {
  event.preventDefault();
  const link = event.target.closest('a');
  const slug = link.getAttribute('to');

  // find corresponding page object
  let pageKey;

  
  for (const key in pages) if (pages[key].slug === slug) pageKey = key;

  // define stateobj and buildpage
  const stateObj = { pageKey: pageKey };
  buildPage(stateObj, true);
}

function handleUncertainty(event) {
  uncertainty = event.currentTarget.checked;
  const precipitationGraph = drawPrecipitactionGraphDOM(locationData, defaultYear, uncertainty);
  const graphContainer = document.getElementById('map__contents__details__graph');
  graphContainer.replaceChildren(precipitationGraph);
}

/**
 * setting a new location on the map
 * @param  {Object} latlng Coorinates of the new location as [lat, lng]
 * @todo update everything related to the new location
 */
async function setLocation(latlng, year = 2030) {
  marker.setLatLng(latlng).addTo(map);
  latlong = latlng;
  document.querySelector("div[class=lds-dual-ring]").style.display = "inline-block";
  document.getElementById("map__contents__details__graph").style.display = "none";
  // pan to location on map...
  map.flyTo(latlng, 5);
  // update url

  // update search field input
  const mapEl = document.getElementById('map');
  delete mapEl.dataset.detailsClosed;

  // load and open details view
  locationData = await fetchLocationData(latlng);
  // const precipitationGraph = drawPrecipitationGraphSVG(locationData);
  const precipitationGraph = drawPrecipitactionGraphDOM(locationData, year, uncertainty);
  const graphContainer = document.getElementById('map__contents__details__graph');

  document.querySelector('select[name=climate_change_period]').selectedIndex = 0;
  graphContainer.replaceChildren(precipitationGraph);
}

function clearLocation(event) {
  const mapEl = document.getElementById('map');
  mapEl.dataset.detailsClosed = '';
  mapEl.dataset.detailsAsSheet = '';
  closeAllLists();
  //clear search field input
  const searchInput = document.getElementById('map__contents__navigate__search__input');
  searchInput.value = null;
  // close details view
}

/**
 * detect touch screen device
 * @return {Boolean}      true if touch device detected
 */
function is_touch_enabled() {
  return 'ontouchstart' in window || navigator.maxTouchPoints > 0 || navigator.msMaxTouchPoints > 0;
}

/**
 * toggle aside
 * @return {String}      set target state open/close/(empty = toggle)
 */
function toggleAside(targetState) {
  const attr = 'data-aside-closed';
  const app = document.getElementById('app');

  if (targetState === 'close') app.setAttribute(attr, '');
  else if (targetState === 'open') app.removeAttribute(attr);
  else app.hasAttribute(attr) ? app.removeAttribute(attr) : app.setAttribute(attr, '');
}

/**
 * fetch location data from server
 * @return {Object}      Object with lat and lng coordinates
 * @todo replace static json data with live server request.
 */
async function fetchLocationData(latlng) {
  const response = await fetch(`${process.env.SERVER}/location?lat=${latlng[0]}&lng=${latlng[1]}`);
  return await response.json();
}

/**
 * SVG rendering has been halted due to responsivness issues
 * @return {SVG Element}      SVG Element containing the graph
 * @todo finish responsive svg drawing
 */
function drawPrecipitationGraphSVG(data) {
  const defaultPeriod = 2030;

  // get max value and column count
  const values = [];
  for (let key in data.period[defaultPeriod].years) {
    values.push(data.period[defaultPeriod].years[key].present);
    values.push(data.period[defaultPeriod].years[key].climate_change);
  }

  const maxValue = Math.max(...values);
  const columnCount = Object.keys(data.period[defaultPeriod].years).length;

  // start drawing
  const graphHeight = 300;
  const xLabelHeight = 30;
  const yLabelWidth = 30;
  const fontSize = 15;
  const unit = graphHeight / maxValue;
  //   let maxY = Math.ceil(maxValue / 10) * 10;
  const xmlns = 'http://www.w3.org/2000/svg';
  const graphEl = document.createElementNS(xmlns, 'svg');
  graphEl.classList.add('graph');
  graphEl.setAttributeNS(null, 'height', graphHeight + xLabelHeight);
  graphEl.setAttributeNS(null, 'shape-rendering', 'crispEdges');
  //   graphEl.setAttributeNS(null, "viewBox", "0 0 " + this.width + " " + this.height);
  graphEl.setAttributeNS(null, 'version', '1.1');

  // create svg definitions
  // const defs = document.createElementNS(xmlns, 'defs');
  // graphEl.appendChild(defs);

  // // grid pattern
  // let gridPattern = document.createElementNS(xmlns, 'pattern');
  // graphEl.setAttributeNS(null, 'width', '100%');
  // graphEl.setAttributeNS(null, 'height', unit * 10);
  // defs.appendChild(gridPattern);

  // let rect = document.createElementNS(xmlns, 'rect');
  // rect.setAttributeNS(null, 'x', `${xPos}%`);
  // rect.setAttributeNS(null, 'height', value);
  // gridPattern.appendChild(rect)

  //   console.log(getComputedStyle(document.querySelector("b")).getPropertyValue("--my-custom-property-2"));

  // draw scale
  // make us of <pattern> tag instead
  let scale = document.createElementNS(xmlns, 'g');
  scale.classList.add('precipitation-graph__scale');
  graphEl.appendChild(scale);

  let yStepSizePx = unit * 10;
  let count = graphHeight / yStepSizePx;
  for (let i = 0; i <= count; i++) {
    let yPos = i * yStepSizePx;

    let row = document.createElementNS(xmlns, 'g');
    row.setAttributeNS(null, 'transform', `translate( 0, ${yPos} )`);
    scale.appendChild(row);

    let line = document.createElementNS(xmlns, 'line');
    line.classList.add('row-line');
    line.setAttributeNS(null, 'x1', '0');
    line.setAttributeNS(null, 'x2', '100%');
    line.setAttributeNS(null, 'y1', 0);
    line.setAttributeNS(null, 'y2', 0);
    row.appendChild(line);

    let labelBg = document.createElementNS(xmlns, 'rect');
    labelBg.classList.add('row-labelbg');
    labelBg.setAttributeNS(null, 'x', 0);
    labelBg.setAttributeNS(null, 'y', fontSize - yStepSizePx);
    labelBg.setAttributeNS(null, 'width', yLabelWidth);
    labelBg.setAttributeNS(null, 'height', fontSize);
    row.appendChild(labelBg);

    let label = document.createElementNS(xmlns, 'text');
    label.classList.add('row-label');
    label.setAttributeNS(null, 'x', 0);
    label.setAttributeNS(null, 'y', fontSize - yStepSizePx / 2);
    label.textContent = parseInt((count - i) * 10);
    row.appendChild(label);
  }

  // draw columns
  let columns = document.createElementNS(xmlns, 'g');
  columns.classList.add('precipitation-graph__columns');
  graphEl.appendChild(columns);

  let yearObj = data.period[defaultPeriod].years;
  let xStepSizePct = 100 / (columnCount + 1);
  let index = 1;

  for (let years in yearObj) {
    let value = yearObj[years].present;
    let valuePx = unit * value;
    let xPos = index * xStepSizePct;

    let column = document.createElementNS(xmlns, 'g');
    column.classList.add('column');
    column.setAttributeNS(null, 'transform', `translate( 0, 0 )`);
    columns.appendChild(column);

    let rect = document.createElementNS(xmlns, 'rect');
    rect.classList.add('rect-present');
    rect.setAttributeNS(null, 'x', `${xPos}%`);
    rect.setAttributeNS(null, 'y', 0);
    rect.setAttributeNS(null, 'height', valuePx);
    column.appendChild(rect);

    let columnLabel = document.createElementNS(xmlns, 'text');
    columnLabel.classList.add('column-label');
    columnLabel.setAttributeNS(null, 'x', `${xPos}%`);
    columnLabel.setAttributeNS(null, 'y', fontSize);
    columnLabel.textContent = years + 'y';
    column.appendChild(columnLabel);

    let valueLabel = document.createElementNS(xmlns, 'text');
    valueLabel.classList.add('column-value');
    valueLabel.setAttributeNS(null, 'x', `${xPos}%`);
    valueLabel.setAttributeNS(null, 'y', valuePx);
    valueLabel.textContent = value;
    column.appendChild(valueLabel);

    index++;
  }

  return graphEl;
}

/**
 * rendering the location data as a graph for precipitation events
 * for now SVG has been replaced with DOM elements for faster development.
 * @return {DOM Element}      DOM Element containing the graph
 * @todo Replace this with SVG in the future
 */
function drawPrecipitactionGraphDOM(data, defaultPeriod = 2030, uncert = false) {
  let rowLabelStepSize = 20;

  document.querySelector("div[class=lds-dual-ring]").style.display = "none";
  document.getElementById("map__contents__details__graph").style.display = "inline-block";
  // get max value and column count
  const values = [];
  for (let key in data.period[defaultPeriod].years) {
    const present = data.period[defaultPeriod].years[key].present;
    values.push(present);
    values.push(data.period[defaultPeriod].years[key].climate_change);
    if (uncert) values.push(present * 1.3);
  }

  const maxValue = Math.max(...values);
  if (maxValue > 299) rowLabelStepSize = 50;
  if (maxValue > 599) rowLabelStepSize = 100;
  const ceiledMaxValue = Math.ceil(maxValue / rowLabelStepSize) * rowLabelStepSize;
  const rowCount = ceiledMaxValue / rowLabelStepSize;
  const yearObj = data.period[defaultPeriod].years;
  const unitPct = 100 / ceiledMaxValue;

  let graph = document.createElement('div');
  graph.classList.add('graph-precip');

  // draw header
  let header = document.createElement('div');
  header.classList.add('header');
  graph.appendChild(header);

  let units = document.createElement('div');
  units.classList.add('units');
  units.innerHTML = `${translate('unit')}`;
  header.appendChild(units);

  let legend = document.createElement('ul');
  legend.classList.add('legend');
  legend.innerHTML = `<li>${translate('climate_change')}</li>
    <li>${translate('present')}</li>`;
  header.appendChild(legend);

  // draw row labels and row lines
  let rowLabelSection = document.createElement('div');
  rowLabelSection.classList.add('row-label-section');
  graph.appendChild(rowLabelSection);

  let rowLinesSection = document.createElement('div');
  rowLinesSection.classList.add('row-lines-section');
  graph.appendChild(rowLinesSection);

  for (let i = 0; i <= rowCount; i++) {
    let rowLabel = document.createElement('div');
    rowLabel.classList.add('row-label');
    // rowLabel.innerHTML = i * rowLabelStepSize;
    rowLabel.dataset.value = i * rowLabelStepSize;
    rowLabelSection.appendChild(rowLabel);

    let rowLine = document.createElement('div');
    rowLine.classList.add('row-line');
    rowLinesSection.appendChild(rowLine);
  }

  // draw column labels container
  let columnLabelSection = document.createElement('div');
  columnLabelSection.classList.add('column-label-section');
  graph.appendChild(columnLabelSection);

  // draw graph items container (layer one)
  let graphSectionOne = document.createElement('div');
  graphSectionOne.classList.add('graph-section');
  graph.appendChild(graphSectionOne);

  // draw graph items container (layer two)
  let graphSectionTwo = document.createElement('div');
  graphSectionTwo.classList.add('graph-section');
  graphSectionTwo.classList.add('graph-section-layer');
  graph.appendChild(graphSectionTwo);

  for (let years in yearObj) {
    // draw column labels
    let columnLabel = document.createElement('div');
    columnLabel.classList.add('column-label');
    columnLabel.innerHTML = years;
    columnLabelSection.appendChild(columnLabel);

    // draw graph items (layer one)
    let value = yearObj[years].climate_change;
    let valuePct = value * unitPct;
    let rect = document.createElement('div');
    rect.classList.add('graph-item');
    rect.classList.add('climate-item');
    rect.style.height = valuePct+'%';
    rect.innerHTML = value;
    graphSectionOne.appendChild(rect);

    // draw graph items (layer one)
    if (uncert) {
      rect.innerHTML = "";
      value = yearObj[years].present;
      const rectText = value; //83
      const uncertMinValue = value * 0.7; //59
      value = value * 1.3; //107
      const uncerHeight = Math.ceil(100 - (rectText * 100 / value));
      valuePct = value * unitPct;
      rect = document.createElement('div');
      const present = document.createElement('div');
      const unc = document.createElement('div');
      const overlap = document.createElement('div');
      const span = document.createElement('span');
      rect.classList.add('graph-item');
      rect.style.height = valuePct+'%';
      present.classList.add('present-item');
      present.style.height = (78 - uncerHeight) + '%';
      unc.classList.add('uncert-item');
      unc.style.height = uncerHeight + '%';
      overlap.style.height = '22%';
      overlap.classList.add('overlap-item');
      span.classList.add('overlap-item-span');
      const uncerValue = Math.ceil(value);
      const uncertMin = Math.floor(uncertMinValue);
      span.innerText = uncertMin; 
      unc.innerHTML = `<div style="color: black; margin-top: -16px">${uncerValue}</div><div style="width: 53%; height: 100%; margin-top: 0px; border-right: #17527c 1px solid; color: black">
      </div>`;
      overlap.innerHTML = '<div style="width: 3%; height: 100%; margin: 0 auto; border-right: #17527c 1px solid;">&nbsp;</div>';
      overlap.appendChild(span);
      rect.appendChild(unc);
      rect.appendChild(overlap);
      rect.appendChild(present);
      graphSectionTwo.appendChild(rect);
    } else {
      value = yearObj[years].present;
      valuePct = value * unitPct;
      rect = document.createElement('div');
      rect.classList.add('graph-item');
      rect.classList.add('present-item');
      rect.style.height = valuePct+'%';
      rect.innerHTML = value;
      graphSectionTwo.appendChild(rect);
  
    }
  }

  return graph;
}

init();

// helper functions
Number.prototype.map = function (in_min, in_max, out_min, out_max) {
  return ((this - in_min) * (out_max - out_min)) / (in_max - in_min) + out_min;
};