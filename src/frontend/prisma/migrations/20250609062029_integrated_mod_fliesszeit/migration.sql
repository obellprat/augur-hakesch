-- AlterTable
ALTER TABLE "Project" ADD COLUMN     "idfParameterId" INTEGER,
ADD COLUMN     "moFliesszeitId" INTEGER;

-- CreateTable
CREATE TABLE "IDF_Parameters" (
    "id" SERIAL NOT NULL,
    "P_low_1h" DOUBLE PRECISION NOT NULL,
    "P_high_1h" DOUBLE PRECISION NOT NULL,
    "P_low_24h" DOUBLE PRECISION NOT NULL,
    "P_high_24h" DOUBLE PRECISION NOT NULL,
    "rp_low" TEXT NOT NULL,
    "rp_high" TEXT NOT NULL,

    CONSTRAINT "IDF_Parameters_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Mod_Fliesszeit" (
    "id" SERIAL NOT NULL,
    "x" INTEGER NOT NULL,
    "Vo20" DOUBLE PRECISION NOT NULL,
    "psi" DOUBLE PRECISION NOT NULL,
    "TB_start" INTEGER NOT NULL,
    "istep" INTEGER NOT NULL,
    "tol" INTEGER NOT NULL,
    "max_iter" INTEGER NOT NULL,

    CONSTRAINT "Mod_Fliesszeit_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Annualities" (
    "id" SERIAL NOT NULL,
    "description" TEXT NOT NULL,

    CONSTRAINT "Annualities_pkey" PRIMARY KEY ("id")
);

-- AddForeignKey
ALTER TABLE "Project" ADD CONSTRAINT "Project_idfParameterId_fkey" FOREIGN KEY ("idfParameterId") REFERENCES "IDF_Parameters"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Project" ADD CONSTRAINT "Project_moFliesszeitId_fkey" FOREIGN KEY ("moFliesszeitId") REFERENCES "Mod_Fliesszeit"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Mod_Fliesszeit" ADD CONSTRAINT "Mod_Fliesszeit_x_fkey" FOREIGN KEY ("x") REFERENCES "Annualities"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
