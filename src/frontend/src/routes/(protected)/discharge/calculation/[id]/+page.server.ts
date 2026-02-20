import { getProjectById, getAllZones } from '$lib/server/project';
import { error } from '@sveltejs/kit';
import { fail, redirect } from '@sveltejs/kit';
import type { Actions } from './$types';
import { base } from '$app/paths';
import { browser } from '$app/environment';
import { page } from '$app/state';
import { prisma } from '$lib/prisma';
import type { ZoneParameter } from '../../../../../../prisma/src/generated/prisma/client';

type BulkScenario<T extends Record<string, unknown>> = {
	ids?: number[];
	project_id?: string;
} & T;

type BulkPayload = {
	idf?: {
		idf_id?: number | null;
		P_low_1h?: number;
		P_high_1h?: number;
		P_low_24h?: number;
		P_high_24h?: number;
		rp_low?: number;
		rp_high?: number;
	} | null;
	modFliesszeit?: BulkScenario<{ Vo20?: number; psi?: number }>[] | null;
	koella?: BulkScenario<{ Vo20?: number; glacier_area?: number }>[] | null;
	clarkWSL?: BulkScenario<{ fractions?: Record<string, number> }>[] | null;
	nam?: BulkScenario<{
		precipitation_factor?: number;
		readiness_to_drain?: number;
		water_balance_mode?: string;
		storm_center_mode?: string;
		routing_method?: string;
	}>[] | null;
};

export const load = async ({ params }) => {
	if (browser) {
		if (!page.data.session?.user?.name) {
			redirect(303, `./login?redirect_url=` + page.url.href + '/discharge');
		}
	}

	const { id } = params;
	const project = await getProjectById(id);
	const zones = await getAllZones();
	if (!project) {
		error(404, 'Project not found');
	}

	return {
		project,
		zones
	};
};

export const actions = {
	updatefnp: async ({ request }) => {
		const formData = Object.fromEntries(await request.formData());
		const { id, idf_id, P_low_1h, P_high_1h, P_low_24h, P_high_24h, rp_low, rp_high } =
			formData as unknown as {
				id: string | undefined;
				idf_id: number | undefined;
				P_low_1h: number | undefined;
				P_high_1h: number | undefined;
				P_low_24h: number | undefined;
				P_high_24h: number | undefined;
				rp_low: number | undefined;
				rp_high: number | undefined;
			};
		if (!id) {
			return fail(400, { message: 'Missing required fields' });
		}

		const idf = await prisma.IDF_Parameters.upsert({
			where: { id: Number(idf_id) || 0 },
			update: {
				P_low_1h: Number(P_low_1h) || 0,
				P_high_1h: Number(P_high_1h) || 0,
				P_low_24h: Number(P_low_24h) || 0,
				P_high_24h: Number(P_high_24h) || 0,
				rp_low: Number(rp_low) || 0,
				rp_high: Number(rp_high) || 0
			},
			create: {
				P_low_1h: Number(P_low_1h) || 0,
				P_high_1h: Number(P_high_1h) || 0,
				P_low_24h: Number(P_low_24h) || 0,
				P_high_24h: Number(P_high_24h) || 0,
				rp_low: Number(rp_low) || 0,
				rp_high: Number(rp_high) || 0
			}
		});

		await prisma.project.update({
			where: { id: id! },
			data: {
				IDF_Parameters: {
					connect: {
						id: idf.id
					}
				}
			}
		});

		redirect(302, `${base}/discharge/calculation/${id}`);
	},

	updatemfzv: async ({ request }) => {
		const formData = Object.fromEntries(await request.formData());
		const { id, mfzv_id, x, Vo20, psi } = formData as unknown as {
			id: string | undefined;
			mfzv_id: number | undefined;
			x: number | undefined;
			Vo20: number | undefined;
			psi: number | undefined;
		};

		if (!id) {
			return fail(400, { message: 'Missing required fields' });
		}
		const annuality = await prisma.Annualities.findUnique({
			where: {
				number: Number(x) || 0
			}
		});
		const mfzv = await prisma.Mod_Fliesszeit.upsert({
			where: {
				id: Number(mfzv_id) || 0
			},
			update: {
				Annuality: {
					connect: {
						id: annuality.id
					}
				},
				Vo20: Number(Vo20) || 0,
				psi: Number(psi) || 0
			},
			create: {
				Annuality: {
					connect: {
						number: Number(x) || 0
					}
				},
				Vo20: Number(Vo20) || 0,
				psi: Number(psi) || 0,
				Project: {
					connect: {
						id: id
					}
				}
			}
		});

		const project = await prisma.project.update({
			where: { id: id! },
			data: {
				Mod_Fliesszeit: {
					connect: {
						id: mfzv.id
					}
				}
			},
			include: {
				Point: true,
				IDF_Parameters: true,
				Mod_Fliesszeit: {
					orderBy: {
						id: 'asc'
					},
					include: {
						Annuality: true,
						Mod_Fliesszeit_Result: true
					}
				}
			}
		});
		return project;
		//redirect(302, `${base}/discharge/calculation/${id}`);
	},

	updatekoella: async ({ request }) => {
		const formData = Object.fromEntries(await request.formData());
		const { id, koella_id, x, Vo20, glacier_area } = formData as unknown as {
			id: string | undefined;
			koella_id: number | undefined;
			x: number | undefined;
			Vo20: number | undefined;
			glacier_area: number | undefined;
		};

		if (!id) {
			return fail(400, { message: 'Missing required fields' });
		}
		const annuality = await prisma.Annualities.findUnique({
			where: {
				number: Number(x) || 0
			}
		});
		const newkoella = await prisma.Koella.upsert({
			where: {
				id: Number(koella_id) || 0
			},
			update: {
				Annuality: {
					connect: {
						id: annuality.id
					}
				},
				Vo20: Number(Vo20) || 0,
				glacier_area: Number(glacier_area) || 0
			},
			create: {
				Annuality: {
					connect: {
						number: Number(x) || 0
					}
				},
				Vo20: Number(Vo20) || 0,
				glacier_area: Number(glacier_area) || 0,
				Project: {
					connect: {
						id: id
					}
				}
			}
		});
		const project = await prisma.project.update({
			where: { id: id! },
			data: {
				Koella: {
					connect: {
						id: newkoella.id
					}
				}
			},
			include: {
				Point: true,
				IDF_Parameters: true,
				Koella: {
					orderBy: {
						id: 'asc'
					},
					include: {
						Annuality: true,
						Koella_Result: true
					}
				}
			}
		});
		return project;
		//redirect(302, `${base}/discharge/calculation/${id}`);
	},

	updateclarkwsl: async ({ request }) => {
		const formData = Object.fromEntries(await request.formData());
		const { id, clarkwsl_id, x, zone_0, zone_1, zone_2, zone_3, zone_4, zone_5, zone_6, zone_7 } =
			formData as unknown as {
				id: string | undefined;
				clarkwsl_id: number | undefined;
				x: number | undefined;
				zone_0: number | undefined;
				zone_1: number | undefined;
				zone_2: number | undefined;
				zone_3: number | undefined;
				zone_4: number | undefined;
				zone_5: number | undefined;
				zone_6: number | undefined;
				zone_7: number | undefined;
			};

		if (!id) {
			return fail(400, { message: 'Missing required fields' });
		}
		const annuality = await prisma.Annualities.findUnique({
			where: {
				number: Number(x) || 0
			}
		});
		const newclarkwsl = await prisma.ClarkWSL.upsert({
			where: {
				id: Number(clarkwsl_id) || 0
			},
			update: {
				Annuality: {
					connect: {
						id: annuality.id
					}
				}
			},
			create: {
				Annuality: {
					connect: {
						number: Number(x) || 0
					}
				},
				Project: {
					connect: {
						id: id
					}
				}
			}
		});

		const zones = await getAllZones();

		await prisma.Fractions.deleteMany({
			where: {
				ClarkWSL: {
					id: newclarkwsl.id
				}
			}
		});

		const fractions = zones.map((zone: ZoneParameter, index: number) => ({
			ZoneParameterTyp: zone.typ,
			pct: Number(formData[`zone_${index}`]) || 0,
			clarkwsl_id: newclarkwsl.id
		}));

		await prisma.Fractions.createMany({
			data: fractions,
			skipDuplicates: true
		});

		const project = await prisma.project.update({
			where: { id: id! },
			data: {
				ClarkWSL: {
					connect: {
						id: newclarkwsl.id
					}
				}
			},
			include: {
				Point: true,
				IDF_Parameters: true,
				ClarkWSL: {
					orderBy: {
						id: 'asc'
					},
					include: {
						Annuality: true,
						ClarkWSL_Result: true
					}
				}
			}
		});
		return project;
	},

	updatenam: async ({ request }) => {
		const formData = Object.fromEntries(await request.formData());
		const { id, nam_id, x, precipitation_factor, readiness_to_drain, water_balance_mode, storm_center_mode, routing_method } = formData as unknown as {
			id: string | undefined;
			nam_id: number | undefined;
			x: number | undefined;
			precipitation_factor: number | undefined;
			readiness_to_drain: number | undefined;
			water_balance_mode: string | undefined;
			storm_center_mode: string | undefined;
			routing_method: string | undefined;
		};

		if (!id) {
			return fail(400, { message: 'Missing required fields' });
		}
		
		const annuality = await prisma.Annualities.findUnique({
			where: {
				number: Number(x) || 0
			}
		});

		if (!annuality) {
			return fail(400, { message: 'Invalid return period' });
		}

		// Validate that the mode values exist in their respective tables
		const validWaterBalanceMode = water_balance_mode || "uniform";
		const validStormCenterMode = storm_center_mode || "centroid";
		const validRoutingMethod = routing_method || "time_values";

		// Check if the mode values exist in their respective tables
		const [waterBalanceModeExists, stormCenterModeExists, routingMethodExists] = await Promise.all([
			prisma.WaterBalanceMode.findUnique({ where: { mode: validWaterBalanceMode } }),
			prisma.StormCenterMode.findUnique({ where: { mode: validStormCenterMode } }),
			prisma.RoutingMethod.findUnique({ where: { method: validRoutingMethod } })
		]);

		if (!waterBalanceModeExists) {
			return fail(400, { message: 'Invalid water balance mode' });
		}
		if (!stormCenterModeExists) {
			return fail(400, { message: 'Invalid storm center mode' });
		}
		if (!routingMethodExists) {
			return fail(400, { message: 'Invalid routing method' });
		}

		const newnam = await prisma.NAM.upsert({
			where: {
				id: Number(nam_id) || 0
			},
			update: {
				Annuality: {
					connect: {
						id: annuality.id
					}
				},
				precipitation_factor: Number(precipitation_factor) || 0.748,
				readiness_to_drain: Number(readiness_to_drain) || 0,
				WaterBalanceMode: {
					connect: {
						mode: validWaterBalanceMode
					}
				},
				StormCenterMode: {
					connect: {
						mode: validStormCenterMode
					}
				},
				RoutingMethod: {
					connect: {
						method: validRoutingMethod
					}
				}
			},
			create: {
				Annuality: {
					connect: {
						number: Number(x) || 0
					}
				},
				precipitation_factor: Number(precipitation_factor) || 0.748,
				readiness_to_drain: Number(readiness_to_drain) || 0,
				WaterBalanceMode: {
					connect: {
						mode: validWaterBalanceMode
					}
				},
				StormCenterMode: {
					connect: {
						mode: validStormCenterMode
					}
				},
				RoutingMethod: {
					connect: {
						method: validRoutingMethod
					}
				},
				Project: {
					connect: {
						id: id
					}
				}
			}
		});
		
		const project = await prisma.project.update({
			where: { id: id! },
			data: {
				NAM: {
					connect: {
						id: newnam.id
					}
				}
			},
			include: {
				Point: true,
				IDF_Parameters: true,
				NAM: {
					orderBy: {
						id: 'asc'
					},
					include: {
						Annuality: true,
						NAM_Result: true
					}
				}
			}
		});
		return project;
	},

	delete: async ({ request }) => {
		const formData = Object.fromEntries(await request.formData());
		const { id } = formData as unknown as {
			id: number | undefined;
		};

		await await prisma.Mod_Fliesszeit.delete({
			where: {
				id: Number(id)
			}
		});
	},

	deleteKoella: async ({ request }) => {
		const formData = Object.fromEntries(await request.formData());
		const { id } = formData as unknown as {
			id: number | undefined;
		};

		await await prisma.Koella.delete({
			where: {
				id: Number(id)
			}
		});
	},

	deleteClarWSL: async ({ request }) => {
		const formData = Object.fromEntries(await request.formData());
		const { id } = formData as unknown as {
			id: number | undefined;
		};

		await await prisma.Fractions.deleteMany({
			where: {
				clarkwsl_id: Number(id)
			}
		});

		await prisma.ClarkWSL.delete({
			where: {
				id: Number(id)
			}
		});
	},

	deleteNAM: async ({ request }) => {
		const formData = Object.fromEntries(await request.formData());
		const { id } = formData as unknown as {
			id: number | undefined;
		};

		await prisma.NAM.delete({
			where: {
				id: Number(id)
			}
		});
	},

	deleteScenario: async ({ request }) => {
		const formData = await request.formData();
		const ids = formData.getAll('ids[]') as string[];
		const type = formData.get('type') as string;

		if (!ids || ids.length === 0 || !type) {
			return fail(400, { message: 'Missing required fields' });
		}

		// Delete all entries for this scenario (3 annualities)
		const numericIds = ids.map((id) => Number(id));

		switch (type) {
			case 'modfliesszeit':
				await prisma.Mod_Fliesszeit.deleteMany({
					where: {
						id: {
							in: numericIds
						}
					}
				});
				break;
			case 'koella':
				await prisma.Koella.deleteMany({
					where: {
						id: {
							in: numericIds
						}
					}
				});
				break;
			case 'clarkwsl':
				// First delete fractions for all ClarkWSL entries
				await prisma.Fractions.deleteMany({
					where: {
						clarkwsl_id: {
							in: numericIds
						}
					}
				});
				// Then delete the ClarkWSL entries
				await prisma.ClarkWSL.deleteMany({
					where: {
						id: {
							in: numericIds
						}
					}
				});
				break;
			case 'nam':
				await prisma.NAM.deleteMany({
					where: {
						id: {
							in: numericIds
						}
					}
				});
				break;
			default:
				return fail(400, { message: 'Invalid calculation type' });
		}

		return { success: true };
	},

	updateScenario: async ({ request }) => {
		// Read formData once (can't read request body multiple times)
		const formDataRaw = await request.formData();
		const ids = formDataRaw.getAll('ids[]') as string[];
		const type = formDataRaw.get('type') as string;
		const project_id = formDataRaw.get('project_id') as string;

		if (!ids || ids.length === 0 || !type) {
			return fail(400, { message: 'Missing required fields' });
		}

		const numericIds = ids.map((id) => Number(id));

		// Update all entries in the scenario with the same values
		switch (type) {
			case 'modfliesszeit':
				const Vo20 = Number(formDataRaw.get('Vo20')) || 0;
				const psi = Number(formDataRaw.get('psi')) || 0;
				
				for (const id of numericIds) {
					await prisma.Mod_Fliesszeit.update({
						where: { id },
						data: { Vo20, psi }
					});
				}
				break;

			case 'koella':
				const kVo20 = Number(formDataRaw.get('Vo20')) || 0;
				const glacier_area = Number(formDataRaw.get('glacier_area')) || 0;
				
				for (const id of numericIds) {
					await prisma.Koella.update({
						where: { id },
						data: { Vo20: kVo20, glacier_area }
					});
				}
				break;

			case 'clarkwsl':
				const zones = await getAllZones();
				
				for (const id of numericIds) {
					// Delete existing fractions
					await prisma.Fractions.deleteMany({
						where: { clarkwsl_id: id }
					});
					
					// Create new fractions
					const fractions = zones.map((zone: ZoneParameter, index: number) => ({
						ZoneParameterTyp: zone.typ,
						pct: Number(formDataRaw.get(`zone_${index}`)) || 0,
						clarkwsl_id: id
					}));
					
					await prisma.Fractions.createMany({
						data: fractions,
						skipDuplicates: true
					});
				}
				break;

			case 'nam':
				const precipitation_factor = Number(formDataRaw.get('precipitation_factor')) || 0.748;
				console.log(precipitation_factor);
				const readiness_to_drain = Number(formDataRaw.get('readiness_to_drain')) || 0;
				const water_balance_mode = (formDataRaw.get('water_balance_mode') as string) || 'uniform';
				const storm_center_mode = (formDataRaw.get('storm_center_mode') as string) || 'centroid';
				const routing_method = (formDataRaw.get('routing_method') as string) || 'time_values';
				
				for (const id of numericIds) {
					await prisma.NAM.update({
						where: { id },
						data: {
							precipitation_factor,
							readiness_to_drain,
							water_balance_mode,
							storm_center_mode,
							routing_method
						}
					});
				}
				break;

			default:
				return fail(400, { message: 'Invalid calculation type' });
		}

		// Return updated project
		const project = await prisma.project.findUnique({
			where: { id: project_id },
			include: {
				Point: true,
				IDF_Parameters: true,
				Mod_Fliesszeit: {
					orderBy: { id: 'asc' },
					include: { Annuality: true, Mod_Fliesszeit_Result: true }
				},
				Koella: {
					orderBy: { id: 'asc' },
					include: { Annuality: true, Koella_Result: true }
				},
				ClarkWSL: {
					orderBy: { id: 'asc' },
					include: { Annuality: true, ClarkWSL_Result: true, Fractions: true }
				},
				NAM: {
					orderBy: { id: 'asc' },
					include: { Annuality: true, NAM_Result: true }
				}
			}
		});

		return project;
	},

	bulkSave: async ({ request }) => {
		const formData = await request.formData();
		const projectId = formData.get('project_id') as string | null;
		const payloadRaw = formData.get('payload') as string | null;

		if (!projectId || !payloadRaw) {
			return fail(400, { message: 'Missing required fields' });
		}

		let payload: BulkPayload;
		try {
			payload = JSON.parse(payloadRaw) as BulkPayload;
		} catch (error) {
			return fail(400, { message: 'Invalid payload format' });
		}

		const normalizedProjectId = projectId;

		if (payload.idf) {
			const {
				idf_id,
				P_low_1h,
				P_high_1h,
				P_low_24h,
				P_high_24h,
				rp_low,
				rp_high
			} = payload.idf;

			const idfRecord = await prisma.IDF_Parameters.upsert({
				where: { id: Number(idf_id) || 0 },
				update: {
					P_low_1h: Number(P_low_1h) || 0,
					P_high_1h: Number(P_high_1h) || 0,
					P_low_24h: Number(P_low_24h) || 0,
					P_high_24h: Number(P_high_24h) || 0,
					rp_low: Number(rp_low) || 0,
					rp_high: Number(rp_high) || 0
				},
				create: {
					P_low_1h: Number(P_low_1h) || 0,
					P_high_1h: Number(P_high_1h) || 0,
					P_low_24h: Number(P_low_24h) || 0,
					P_high_24h: Number(P_high_24h) || 0,
					rp_low: Number(rp_low) || 0,
					rp_high: Number(rp_high) || 0
				}
			});

			await prisma.project.update({
				where: { id: normalizedProjectId },
				data: {
					IDF_Parameters: {
						connect: {
							id: idfRecord.id
						}
					}
				}
			});
		}

		if (Array.isArray(payload.modFliesszeit)) {
			for (const scenario of payload.modFliesszeit) {
				const ids = (scenario.ids || []).map((id) => Number(id)).filter((id) => id > 0);
				if (!ids.length) continue;
				const Vo20 = Number(scenario.Vo20) || 0;
				const psi = Number(scenario.psi) || 0;

				for (const id of ids) {
					await prisma.Mod_Fliesszeit.update({
						where: { id },
						data: {
							Vo20,
							psi
						}
					});
				}
			}
		}

		if (Array.isArray(payload.koella)) {
			for (const scenario of payload.koella) {
				const ids = (scenario.ids || []).map((id) => Number(id)).filter((id) => id > 0);
				if (!ids.length) continue;
				const Vo20 = Number(scenario.Vo20) || 0;
				const glacier_area = Number(scenario.glacier_area) || 0;

				for (const id of ids) {
					await prisma.Koella.update({
						where: { id },
						data: {
							Vo20,
							glacier_area
						}
					});
				}
			}
		}

		if (Array.isArray(payload.clarkWSL)) {
			for (const scenario of payload.clarkWSL) {
				const ids = (scenario.ids || []).map((id) => Number(id)).filter((id) => id > 0);
				if (!ids.length) continue;
				const fractions = scenario.fractions ?? {};

				for (const id of ids) {
					await prisma.Fractions.deleteMany({
						where: {
							clarkwsl_id: id
						}
					});

					const entries = Object.entries(fractions).map(([ZoneParameterTyp, pct]) => ({
						ZoneParameterTyp,
						pct: Number(pct) || 0,
						clarkwsl_id: id
					}));

					if (entries.length) {
						await prisma.Fractions.createMany({
							data: entries,
							skipDuplicates: true
						});
					}
				}
			}
		}

		if (Array.isArray(payload.nam)) {
			for (const scenario of payload.nam) {
				const ids = (scenario.ids || []).map((id) => Number(id)).filter((id) => id > 0);
				if (!ids.length) continue;
				const precipitation_factor =
					Number(scenario.precipitation_factor) || 0.748;
				const readiness_to_drain =
					Number(scenario.readiness_to_drain) || 0;
				const water_balance_mode = scenario.water_balance_mode || 'uniform';
				const storm_center_mode = scenario.storm_center_mode || 'centroid';
				const routing_method = scenario.routing_method || 'time_values';

				for (const id of ids) {
					await prisma.NAM.update({
						where: { id },
						data: {
							precipitation_factor,
							readiness_to_drain,
							water_balance_mode,
							storm_center_mode,
							routing_method
						}
					});
				}
			}
		}

		const project = await prisma.project.findUnique({
			where: { id: normalizedProjectId },
			include: {
				Point: true,
				IDF_Parameters: true,
				Mod_Fliesszeit: {
					orderBy: { id: 'asc' },
					include: { Annuality: true, Mod_Fliesszeit_Result: true }
				},
				Koella: {
					orderBy: { id: 'asc' },
					include: { Annuality: true, Koella_Result: true }
				},
				ClarkWSL: {
					orderBy: { id: 'asc' },
					include: { Annuality: true, ClarkWSL_Result: true, Fractions: true }
				},
				NAM: {
					orderBy: { id: 'asc' },
					include: { Annuality: true, NAM_Result: true }
				}
			}
		});

		if (!project) {
			return fail(404, { message: 'Project not found' });
		}

		return project;
	}
} satisfies Actions;
