-- CreateTable
CREATE TABLE "ClarkWSL" (
    "id" SERIAL NOT NULL,
    "x" INTEGER NOT NULL,
    "dt" INTEGER NOT NULL DEFAULT 10,
    "pixel_area_m2" INTEGER NOT NULL DEFAULT 25,
    "project_id" TEXT NOT NULL,
    "clarkwsl_result_id" INTEGER,

    CONSTRAINT "ClarkWSL_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Fractions" (
    "id" SERIAL NOT NULL,
    "ZoneParameterTyp" TEXT NOT NULL,
    "pct" DOUBLE PRECISION NOT NULL,
    "clarkwsl_id" INTEGER NOT NULL,

    CONSTRAINT "Fractions_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "ZoneParameter" (
    "typ" TEXT NOT NULL,
    "V0_20" DOUBLE PRECISION NOT NULL,
    "WSV" DOUBLE PRECISION NOT NULL,
    "psi" DOUBLE PRECISION NOT NULL,
    "alpha" DOUBLE PRECISION NOT NULL,

    CONSTRAINT "ZoneParameter_pkey" PRIMARY KEY ("typ")
);

-- CreateTable
CREATE TABLE "ClarkWSL_Result" (
    "id" SERIAL NOT NULL,
    "Q" DOUBLE PRECISION NOT NULL,
    "W" DOUBLE PRECISION NOT NULL,
    "K" DOUBLE PRECISION NOT NULL,
    "Tc" DOUBLE PRECISION NOT NULL,

    CONSTRAINT "ClarkWSL_Result_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "ClarkWSL_clarkwsl_result_id_key" ON "ClarkWSL"("clarkwsl_result_id");

-- AddForeignKey
ALTER TABLE "ClarkWSL" ADD CONSTRAINT "ClarkWSL_x_fkey" FOREIGN KEY ("x") REFERENCES "Annualities"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "ClarkWSL" ADD CONSTRAINT "ClarkWSL_project_id_fkey" FOREIGN KEY ("project_id") REFERENCES "Project"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "ClarkWSL" ADD CONSTRAINT "ClarkWSL_clarkwsl_result_id_fkey" FOREIGN KEY ("clarkwsl_result_id") REFERENCES "ClarkWSL_Result"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Fractions" ADD CONSTRAINT "Fractions_ZoneParameterTyp_fkey" FOREIGN KEY ("ZoneParameterTyp") REFERENCES "ZoneParameter"("typ") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Fractions" ADD CONSTRAINT "Fractions_clarkwsl_id_fkey" FOREIGN KEY ("clarkwsl_id") REFERENCES "ClarkWSL"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
