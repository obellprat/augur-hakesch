-- CreateTable
CREATE TABLE "Mod_Fliesszeit_Result" (
    "id" SERIAL NOT NULL,
    "HQ" DOUBLE PRECISION NOT NULL,
    "Tc" DOUBLE PRECISION NOT NULL,
    "TB" DOUBLE PRECISION NOT NULL,
    "TFl" DOUBLE PRECISION NOT NULL,
    "i" DOUBLE PRECISION NOT NULL,
    "Vox" DOUBLE PRECISION NOT NULL,
    "mod_fliesszeit" INTEGER NOT NULL,

    CONSTRAINT "Mod_Fliesszeit_Result_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "Mod_Fliesszeit_Result_mod_fliesszeit_key" ON "Mod_Fliesszeit_Result"("mod_fliesszeit");

-- AddForeignKey
ALTER TABLE "Mod_Fliesszeit_Result" ADD CONSTRAINT "Mod_Fliesszeit_Result_mod_fliesszeit_fkey" FOREIGN KEY ("mod_fliesszeit") REFERENCES "Mod_Fliesszeit"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
