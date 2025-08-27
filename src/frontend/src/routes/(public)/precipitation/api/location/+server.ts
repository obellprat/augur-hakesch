import { json } from '@sveltejs/kit';

export async function GET({ url }) {
	const lat = Number(url.searchParams.get('lat') ?? '0');
	const lng = Number(url.searchParams.get('lng') ?? '0');
	const dbResult = await selectLocation(lat, lng);
	// const parsedResult = JSON.parse(dbResult.data);
	console.log(dbResult);

	return json(dbResult);
}

/**
 * Select location entry from local database
 * @param  {String} lat latitude of location
 * @param  {String} lng longitude of location
 */
async function selectLocation(lat: number, lng: number) {
	try {
		/*const result = await prisma.$queryRaw`SELECT * FROM "Precipitation" WHERE lat in (SELECT lat FROM latitude ORDER BY ABS(lat - ${lat}) LIMIT 1) AND lon in (SELECT lon FROM longitude ORDER BY ABS(lon - ${lng}) LIMIT 1);`;


    const years: number[] = [2030, 2050, 2090];
    const periods: number[] = [10, 20, 30, 50, 100];

    const data = { period:
      years.reduce((acc: Record<number, unknown>, year) => {
        acc[year] = {
          years: periods.reduce((pAcc: Record<number, unknown>, period) => {
            pAcc[period] = {
              present: result[`year${period}`],
              climate_change: result[`year${period}_cchange${year}`]
            };
            return pAcc;
          }, {})
        };
        return acc;
      }, {})
    };*/
		// Simulated data for demonstration purposes
		const jsonstring =
			'{"period":{"2030":{"years":{"10":{"present":58,"climate_change":70},"20":{"present":66,"climate_change":80},"30":{"present":70,"climate_change":85},"50":{"present":76,"climate_change":92},"100":{"present":84,"climate_change":102}}},"2050":{"years":{"10":{"present":58,"climate_change":80},"20":{"present":66,"climate_change":91},"30":{"present":70,"climate_change":97},"50":{"present":76,"climate_change":105},"100":{"present":84,"climate_change":116}}},"2090":{"years":{"10":{"present":58,"climate_change":103},"20":{"present":66,"climate_change":117},"30":{"present":70,"climate_change":125},"50":{"present":76,"climate_change":135},"100":{"present":84,"climate_change":150}}}}}';
		return JSON.parse(jsonstring);
		//return data;
	} catch (error) {
		console.log(error);
	}
}
