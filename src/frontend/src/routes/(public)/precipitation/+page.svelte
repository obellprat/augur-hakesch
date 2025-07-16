<script lang="ts">
	import { onMount } from 'svelte';
	import pageTitle from '$lib/page/pageTitle';
	import { _ } from 'svelte-i18n'

    import 'leaflet/dist/leaflet.css';

	$pageTitle = $_('page.precipitation.title');

    onMount(async () => {
        
        const L = (await import('leaflet')).default
         // configure tile laye
        let baseLayer = L.tileLayer('https://tiles.stadiamaps.com/tiles/stamen_toner_lite/{z}/{x}/{y}{r}.png', {
            attribution: 'Map tiles by <a href="http://augur.world">AUGUR</a> and &copy; <a href="https://www.stadiamaps.com/" target="_blank">Stadia Maps</a> &copy; <a href="https://www.stamen.com/" target="_blank">Stamen Design</a> &copy; <a href="https://openmaptiles.org/" target="_blank">OpenMapTiles</a> &copy; <a href="https://www.openstreetmap.org/about/" target="_blank">OpenStreetMap contributors</a>',
            subdomains: 'abcd',
            minZoom: 0,
            maxZoom: 20,
            opacity: 0.5,
        });

        let tilesPeriod = 20

        // https://obellprat.github.io/tilesaugur/tiles${tilesPeriod}/{z}/{x}/{-y}.png 
        let augurLayer = L.tileLayer(`https://augur.world/tilesaugur/tiles${tilesPeriod}/{z}/{x}/{y}.png`, {
            detectRetina: true,
            opacity: 1,
        });

        // create map
        let map = L.map('map__contents__tiles', {
            center: L.latLng(0, 0),
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


    });
</script>


<svelte:head>
	<title>{$pageTitle} | AUGUR</title>
</svelte:head>

<div class="page-container">
	<div class="row row-cols-xxl-1 row-cols-md-1 row-cols-1">
		<div class="col">
			<div class="card d-block">
				<div class="card-body">
					<h1 class="card-title">{$_('page.dashboard.welcome')}</h1>
					<p class="card-text">
						<div id="map__contents">
          <div id="map__contents__tiles"></div>
          <div id="map__contents__period">
            <label class="card"
              ><a data-translate="return">Return Period</a>
              <select name="tiles_period">
                <option value="10">10</option>
                <option value="30">30</option>
                <option value="100">100</option>
              </select>
            </label>
          </div>
          <div id="map__contents__tools">
            <button type="button" class="card" id="getLocation">
              <img class="icon" src="./assets/icons/gps_fixed_black_24dp.svg" alt="My Location" />
            </button>
          </div>
          <div id="map__contents__details">
            <section>
              <div id="map__contents__details__topic">
                <ul>
			<li data-selected><a href="#" data-translate="precipitation">Precipitation</a></li>
                </ul>
              </div>
	      <div id="map__contents__details__description"> <a data-translate="expected">Expected daily maximum precipitation.</a></div>
              <div id="map__contents__details__graph">Graph</div>
              <div class="lds-dual-ring"></div>
              <div id="map__contents__details__drag-handle"></div>
              <ul id="map__contents__details__settings">
               <!--  <li>
                  <label
                    >Consider Climate Change
                    <input type="checkbox" name="vehicle1" value="uncertainty" checked />
                  </label>
                </li>  --> 
                <li>
                  <label
		    ><a data-translate="period">Climate Change Period</a>
                    <select name="climate_change_period">
                      <option value="2030">2030</option>
                      <option value="2050">2050</option>
                      <option value="2090">2090</option>
                    </select>
                  </label>
                </li>
	        <li>
                  <label
                    ><a data-translate="uncertainty">Show Uncertainty Range</a>
                    <input type="checkbox" name="uncertainty_check" />
                  </label>
                </li>
              </ul>
              <ul id="map__contents__details__actions">
                <li>
                  <button type="button" name="download">
                    <img class="icon" src="./assets/icons/file_download_black_24dp.svg" alt="Download" />
                  </button>
                </li>
                <li>
                  <button type="button" name="share" class="tooltip">
                    <img class="icon" src="./assets/icons/share_black_24dp.svg" alt="Share" />
                    <label class="tooltiptext">Copied</label>
                  </button>
                </li>
              </ul>
            </section>
          </div>
          <div id="map__contents__navigate">
            <button id="map__contents__navigate__menu-toggle" class="card" type="button">
              <img class="icon" src="./assets/icons/menu_black_24dp.svg" alt="Menu" />
            </button>
            <div id="map__contents__navigate__search" class="card autocomplete">
              <input id="map__contents__navigate__search__input" type="input" placeholder="Find a place..."  data-translate="find_place"/>
              <label for="map__contents__navigate__search__input">
                <img class="icon" src="./assets/icons/search_black_24dp.svg" alt="Search" />
              </label>
              <div id="map__contents__navigate__search__clear">
                <img class="icon" src="./assets/icons/clear_black_24dp.svg" alt="Clear" />
              </div>
            </div>
          </div>
        </div>
				</div>
				<!-- end card-body-->
			</div>
			<!-- end card-->
		</div>
		<!-- end col -->
	</div>
	<!-- end row -->
</div>
    