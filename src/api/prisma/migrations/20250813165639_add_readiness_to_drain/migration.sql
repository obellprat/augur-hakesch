-- CreateTable
CREATE TABLE "public"."User" (
    "id" SERIAL NOT NULL,
    "email" TEXT NOT NULL,
    "name" TEXT,

    CONSTRAINT "User_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."Project" (
    "id" TEXT NOT NULL,
    "title" TEXT NOT NULL,
    "description" TEXT NOT NULL,
    "lastModified" TIMESTAMP(3) NOT NULL,
    "isozones_taskid" TEXT NOT NULL DEFAULT '',
    "isozones_running" BOOLEAN NOT NULL DEFAULT false,
    "catchment_geojson" TEXT NOT NULL DEFAULT '',
    "catchment_area" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "branches_geojson" TEXT NOT NULL DEFAULT '',
    "channel_length" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "cummulative_channel_length" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "delta_h" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "pointId" INTEGER NOT NULL,
    "userId" INTEGER NOT NULL,
    "idfParameterId" INTEGER,

    CONSTRAINT "Project_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."Point" (
    "id" SERIAL NOT NULL,
    "northing" DOUBLE PRECISION NOT NULL,
    "easting" DOUBLE PRECISION NOT NULL,

    CONSTRAINT "Point_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."IDF_Parameters" (
    "id" SERIAL NOT NULL,
    "P_low_1h" DOUBLE PRECISION NOT NULL,
    "P_high_1h" DOUBLE PRECISION NOT NULL,
    "P_low_24h" DOUBLE PRECISION NOT NULL,
    "P_high_24h" DOUBLE PRECISION NOT NULL,
    "rp_low" DOUBLE PRECISION NOT NULL,
    "rp_high" DOUBLE PRECISION NOT NULL,

    CONSTRAINT "IDF_Parameters_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."Mod_Fliesszeit" (
    "id" SERIAL NOT NULL,
    "x" INTEGER NOT NULL,
    "Vo20" DOUBLE PRECISION NOT NULL,
    "psi" DOUBLE PRECISION NOT NULL,
    "TB_start" INTEGER NOT NULL DEFAULT 30,
    "istep" INTEGER NOT NULL DEFAULT 5,
    "tol" INTEGER NOT NULL DEFAULT 5,
    "max_iter" INTEGER NOT NULL DEFAULT 1000,
    "project_id" TEXT NOT NULL,
    "mod_fliesszeit_result_id" INTEGER,

    CONSTRAINT "Mod_Fliesszeit_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."Mod_Fliesszeit_Result" (
    "id" SERIAL NOT NULL,
    "HQ" DOUBLE PRECISION NOT NULL,
    "Tc" DOUBLE PRECISION NOT NULL,
    "TB" DOUBLE PRECISION NOT NULL,
    "TFl" DOUBLE PRECISION NOT NULL,
    "i" DOUBLE PRECISION NOT NULL,
    "Vox" DOUBLE PRECISION NOT NULL,

    CONSTRAINT "Mod_Fliesszeit_Result_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."Koella" (
    "id" SERIAL NOT NULL,
    "x" INTEGER NOT NULL,
    "Vo20" DOUBLE PRECISION NOT NULL,
    "glacier_area" INTEGER NOT NULL,
    "TB_start" INTEGER NOT NULL DEFAULT 30,
    "tol" INTEGER NOT NULL DEFAULT 5,
    "istep" INTEGER NOT NULL DEFAULT 5,
    "max_iter" INTEGER NOT NULL DEFAULT 1000,
    "project_id" TEXT NOT NULL,
    "koella_result_id" INTEGER,

    CONSTRAINT "Koella_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."Koella_Result" (
    "id" SERIAL NOT NULL,
    "HQ" DOUBLE PRECISION NOT NULL,
    "Tc" DOUBLE PRECISION NOT NULL,
    "TB" DOUBLE PRECISION NOT NULL,
    "TFl" DOUBLE PRECISION NOT NULL,
    "FLeff" DOUBLE PRECISION NOT NULL,
    "i_final" DOUBLE PRECISION NOT NULL,
    "i_korrigiert" DOUBLE PRECISION NOT NULL,

    CONSTRAINT "Koella_Result_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."ClarkWSL" (
    "id" SERIAL NOT NULL,
    "x" INTEGER NOT NULL,
    "dt" INTEGER NOT NULL DEFAULT 10,
    "pixel_area_m2" INTEGER NOT NULL DEFAULT 25,
    "project_id" TEXT NOT NULL,
    "clarkwsl_result_id" INTEGER,

    CONSTRAINT "ClarkWSL_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."Fractions" (
    "id" SERIAL NOT NULL,
    "ZoneParameterTyp" TEXT NOT NULL,
    "pct" DOUBLE PRECISION NOT NULL,
    "clarkwsl_id" INTEGER NOT NULL,

    CONSTRAINT "Fractions_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."ZoneParameter" (
    "typ" TEXT NOT NULL,
    "V0_20" DOUBLE PRECISION NOT NULL,
    "WSV" DOUBLE PRECISION NOT NULL,
    "psi" DOUBLE PRECISION NOT NULL,
    "alpha" DOUBLE PRECISION NOT NULL,

    CONSTRAINT "ZoneParameter_pkey" PRIMARY KEY ("typ")
);

-- CreateTable
CREATE TABLE "public"."ClarkWSL_Result" (
    "id" SERIAL NOT NULL,
    "Q" DOUBLE PRECISION NOT NULL,
    "W" DOUBLE PRECISION NOT NULL,
    "K" DOUBLE PRECISION NOT NULL,
    "Tc" DOUBLE PRECISION NOT NULL,

    CONSTRAINT "ClarkWSL_Result_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."NAM" (
    "id" SERIAL NOT NULL,
    "x" INTEGER NOT NULL,
    "precipitation_factor" DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    "water_balance_mode" TEXT NOT NULL DEFAULT 'simple',
    "storm_center_mode" TEXT NOT NULL DEFAULT 'centroid',
    "routing_method" TEXT NOT NULL DEFAULT 'time_values',
    "readiness_to_drain" INTEGER NOT NULL DEFAULT 0,
    "project_id" TEXT NOT NULL,
    "nam_result_id" INTEGER,

    CONSTRAINT "NAM_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."NAM_Result" (
    "id" SERIAL NOT NULL,
    "HQ" DOUBLE PRECISION NOT NULL,
    "Tc" DOUBLE PRECISION NOT NULL,
    "TB" DOUBLE PRECISION NOT NULL,
    "TFl" DOUBLE PRECISION NOT NULL,
    "i" DOUBLE PRECISION NOT NULL,
    "S" DOUBLE PRECISION NOT NULL,
    "Ia" DOUBLE PRECISION NOT NULL,
    "Pe" DOUBLE PRECISION NOT NULL,
    "effective_curve_number" DOUBLE PRECISION,

    CONSTRAINT "NAM_Result_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."Annualities" (
    "id" SERIAL NOT NULL,
    "description" TEXT NOT NULL,
    "number" DOUBLE PRECISION NOT NULL,

    CONSTRAINT "Annualities_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."Precipitation" (
    "id" SERIAL NOT NULL,
    "latitude" DOUBLE PRECISION NOT NULL,
    "longitude" DOUBLE PRECISION NOT NULL,
    "data" TEXT NOT NULL,

    CONSTRAINT "Precipitation_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."WaterBalanceMode" (
    "mode" TEXT NOT NULL,
    "description" TEXT NOT NULL,

    CONSTRAINT "WaterBalanceMode_pkey" PRIMARY KEY ("mode")
);

-- CreateTable
CREATE TABLE "public"."StormCenterMode" (
    "mode" TEXT NOT NULL,
    "description" TEXT NOT NULL,

    CONSTRAINT "StormCenterMode_pkey" PRIMARY KEY ("mode")
);

-- CreateTable
CREATE TABLE "public"."RoutingMethod" (
    "method" TEXT NOT NULL,
    "description" TEXT NOT NULL,

    CONSTRAINT "RoutingMethod_pkey" PRIMARY KEY ("method")
);

-- CreateIndex
CREATE UNIQUE INDEX "User_email_key" ON "public"."User"("email");

-- CreateIndex
CREATE UNIQUE INDEX "Mod_Fliesszeit_mod_fliesszeit_result_id_key" ON "public"."Mod_Fliesszeit"("mod_fliesszeit_result_id");

-- CreateIndex
CREATE UNIQUE INDEX "Koella_koella_result_id_key" ON "public"."Koella"("koella_result_id");

-- CreateIndex
CREATE UNIQUE INDEX "ClarkWSL_clarkwsl_result_id_key" ON "public"."ClarkWSL"("clarkwsl_result_id");

-- CreateIndex
CREATE UNIQUE INDEX "NAM_nam_result_id_key" ON "public"."NAM"("nam_result_id");

-- CreateIndex
CREATE UNIQUE INDEX "Annualities_number_key" ON "public"."Annualities"("number");

-- AddForeignKey
ALTER TABLE "public"."Project" ADD CONSTRAINT "Project_pointId_fkey" FOREIGN KEY ("pointId") REFERENCES "public"."Point"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "public"."Project" ADD CONSTRAINT "Project_userId_fkey" FOREIGN KEY ("userId") REFERENCES "public"."User"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "public"."Project" ADD CONSTRAINT "Project_idfParameterId_fkey" FOREIGN KEY ("idfParameterId") REFERENCES "public"."IDF_Parameters"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "public"."Mod_Fliesszeit" ADD CONSTRAINT "Mod_Fliesszeit_x_fkey" FOREIGN KEY ("x") REFERENCES "public"."Annualities"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "public"."Mod_Fliesszeit" ADD CONSTRAINT "Mod_Fliesszeit_project_id_fkey" FOREIGN KEY ("project_id") REFERENCES "public"."Project"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "public"."Mod_Fliesszeit" ADD CONSTRAINT "Mod_Fliesszeit_mod_fliesszeit_result_id_fkey" FOREIGN KEY ("mod_fliesszeit_result_id") REFERENCES "public"."Mod_Fliesszeit_Result"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "public"."Koella" ADD CONSTRAINT "Koella_x_fkey" FOREIGN KEY ("x") REFERENCES "public"."Annualities"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "public"."Koella" ADD CONSTRAINT "Koella_project_id_fkey" FOREIGN KEY ("project_id") REFERENCES "public"."Project"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "public"."Koella" ADD CONSTRAINT "Koella_koella_result_id_fkey" FOREIGN KEY ("koella_result_id") REFERENCES "public"."Koella_Result"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "public"."ClarkWSL" ADD CONSTRAINT "ClarkWSL_x_fkey" FOREIGN KEY ("x") REFERENCES "public"."Annualities"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "public"."ClarkWSL" ADD CONSTRAINT "ClarkWSL_project_id_fkey" FOREIGN KEY ("project_id") REFERENCES "public"."Project"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "public"."ClarkWSL" ADD CONSTRAINT "ClarkWSL_clarkwsl_result_id_fkey" FOREIGN KEY ("clarkwsl_result_id") REFERENCES "public"."ClarkWSL_Result"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "public"."Fractions" ADD CONSTRAINT "Fractions_ZoneParameterTyp_fkey" FOREIGN KEY ("ZoneParameterTyp") REFERENCES "public"."ZoneParameter"("typ") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "public"."Fractions" ADD CONSTRAINT "Fractions_clarkwsl_id_fkey" FOREIGN KEY ("clarkwsl_id") REFERENCES "public"."ClarkWSL"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "public"."NAM" ADD CONSTRAINT "NAM_x_fkey" FOREIGN KEY ("x") REFERENCES "public"."Annualities"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "public"."NAM" ADD CONSTRAINT "NAM_water_balance_mode_fkey" FOREIGN KEY ("water_balance_mode") REFERENCES "public"."WaterBalanceMode"("mode") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "public"."NAM" ADD CONSTRAINT "NAM_storm_center_mode_fkey" FOREIGN KEY ("storm_center_mode") REFERENCES "public"."StormCenterMode"("mode") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "public"."NAM" ADD CONSTRAINT "NAM_routing_method_fkey" FOREIGN KEY ("routing_method") REFERENCES "public"."RoutingMethod"("method") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "public"."NAM" ADD CONSTRAINT "NAM_project_id_fkey" FOREIGN KEY ("project_id") REFERENCES "public"."Project"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "public"."NAM" ADD CONSTRAINT "NAM_nam_result_id_fkey" FOREIGN KEY ("nam_result_id") REFERENCES "public"."NAM_Result"("id") ON DELETE CASCADE ON UPDATE CASCADE;
