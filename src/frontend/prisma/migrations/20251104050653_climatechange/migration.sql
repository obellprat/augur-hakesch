/*
  Warnings:

  - A unique constraint covering the columns `[clarkwsl_result_1_5_id]` on the table `ClarkWSL` will be added. If there are existing duplicate values, this will fail.
  - A unique constraint covering the columns `[clarkwsl_result_2_id]` on the table `ClarkWSL` will be added. If there are existing duplicate values, this will fail.
  - A unique constraint covering the columns `[clarkwsl_result_3_id]` on the table `ClarkWSL` will be added. If there are existing duplicate values, this will fail.
  - A unique constraint covering the columns `[clarkwsl_result_4_id]` on the table `ClarkWSL` will be added. If there are existing duplicate values, this will fail.
  - A unique constraint covering the columns `[koella_result_1_5_id]` on the table `Koella` will be added. If there are existing duplicate values, this will fail.
  - A unique constraint covering the columns `[koella_result_2_id]` on the table `Koella` will be added. If there are existing duplicate values, this will fail.
  - A unique constraint covering the columns `[koella_result_3_id]` on the table `Koella` will be added. If there are existing duplicate values, this will fail.
  - A unique constraint covering the columns `[koella_result_4_id]` on the table `Koella` will be added. If there are existing duplicate values, this will fail.
  - A unique constraint covering the columns `[mod_fliesszeit_result_1_5_id]` on the table `Mod_Fliesszeit` will be added. If there are existing duplicate values, this will fail.
  - A unique constraint covering the columns `[mod_fliesszeit_result_2_id]` on the table `Mod_Fliesszeit` will be added. If there are existing duplicate values, this will fail.
  - A unique constraint covering the columns `[mod_fliesszeit_result_3_id]` on the table `Mod_Fliesszeit` will be added. If there are existing duplicate values, this will fail.
  - A unique constraint covering the columns `[mod_fliesszeit_result_4_id]` on the table `Mod_Fliesszeit` will be added. If there are existing duplicate values, this will fail.
  - A unique constraint covering the columns `[nam_result_1_5_id]` on the table `NAM` will be added. If there are existing duplicate values, this will fail.
  - A unique constraint covering the columns `[nam_result_2_id]` on the table `NAM` will be added. If there are existing duplicate values, this will fail.
  - A unique constraint covering the columns `[nam_result_3_id]` on the table `NAM` will be added. If there are existing duplicate values, this will fail.
  - A unique constraint covering the columns `[nam_result_4_id]` on the table `NAM` will be added. If there are existing duplicate values, this will fail.

*/
-- AlterTable
ALTER TABLE "ClarkWSL" ADD COLUMN     "clarkwsl_result_1_5_id" INTEGER,
ADD COLUMN     "clarkwsl_result_2_id" INTEGER,
ADD COLUMN     "clarkwsl_result_3_id" INTEGER,
ADD COLUMN     "clarkwsl_result_4_id" INTEGER;

-- AlterTable
ALTER TABLE "Koella" ADD COLUMN     "koella_result_1_5_id" INTEGER,
ADD COLUMN     "koella_result_2_id" INTEGER,
ADD COLUMN     "koella_result_3_id" INTEGER,
ADD COLUMN     "koella_result_4_id" INTEGER;

-- AlterTable
ALTER TABLE "Mod_Fliesszeit" ADD COLUMN     "mod_fliesszeit_result_1_5_id" INTEGER,
ADD COLUMN     "mod_fliesszeit_result_2_id" INTEGER,
ADD COLUMN     "mod_fliesszeit_result_3_id" INTEGER,
ADD COLUMN     "mod_fliesszeit_result_4_id" INTEGER;

-- AlterTable
ALTER TABLE "NAM" ADD COLUMN     "nam_result_1_5_id" INTEGER,
ADD COLUMN     "nam_result_2_id" INTEGER,
ADD COLUMN     "nam_result_3_id" INTEGER,
ADD COLUMN     "nam_result_4_id" INTEGER;

-- CreateIndex
CREATE UNIQUE INDEX "ClarkWSL_clarkwsl_result_1_5_id_key" ON "ClarkWSL"("clarkwsl_result_1_5_id");

-- CreateIndex
CREATE UNIQUE INDEX "ClarkWSL_clarkwsl_result_2_id_key" ON "ClarkWSL"("clarkwsl_result_2_id");

-- CreateIndex
CREATE UNIQUE INDEX "ClarkWSL_clarkwsl_result_3_id_key" ON "ClarkWSL"("clarkwsl_result_3_id");

-- CreateIndex
CREATE UNIQUE INDEX "ClarkWSL_clarkwsl_result_4_id_key" ON "ClarkWSL"("clarkwsl_result_4_id");

-- CreateIndex
CREATE UNIQUE INDEX "Koella_koella_result_1_5_id_key" ON "Koella"("koella_result_1_5_id");

-- CreateIndex
CREATE UNIQUE INDEX "Koella_koella_result_2_id_key" ON "Koella"("koella_result_2_id");

-- CreateIndex
CREATE UNIQUE INDEX "Koella_koella_result_3_id_key" ON "Koella"("koella_result_3_id");

-- CreateIndex
CREATE UNIQUE INDEX "Koella_koella_result_4_id_key" ON "Koella"("koella_result_4_id");

-- CreateIndex
CREATE UNIQUE INDEX "Mod_Fliesszeit_mod_fliesszeit_result_1_5_id_key" ON "Mod_Fliesszeit"("mod_fliesszeit_result_1_5_id");

-- CreateIndex
CREATE UNIQUE INDEX "Mod_Fliesszeit_mod_fliesszeit_result_2_id_key" ON "Mod_Fliesszeit"("mod_fliesszeit_result_2_id");

-- CreateIndex
CREATE UNIQUE INDEX "Mod_Fliesszeit_mod_fliesszeit_result_3_id_key" ON "Mod_Fliesszeit"("mod_fliesszeit_result_3_id");

-- CreateIndex
CREATE UNIQUE INDEX "Mod_Fliesszeit_mod_fliesszeit_result_4_id_key" ON "Mod_Fliesszeit"("mod_fliesszeit_result_4_id");

-- CreateIndex
CREATE UNIQUE INDEX "NAM_nam_result_1_5_id_key" ON "NAM"("nam_result_1_5_id");

-- CreateIndex
CREATE UNIQUE INDEX "NAM_nam_result_2_id_key" ON "NAM"("nam_result_2_id");

-- CreateIndex
CREATE UNIQUE INDEX "NAM_nam_result_3_id_key" ON "NAM"("nam_result_3_id");

-- CreateIndex
CREATE UNIQUE INDEX "NAM_nam_result_4_id_key" ON "NAM"("nam_result_4_id");

-- AddForeignKey
ALTER TABLE "Mod_Fliesszeit" ADD CONSTRAINT "Mod_Fliesszeit_mod_fliesszeit_result_1_5_id_fkey" FOREIGN KEY ("mod_fliesszeit_result_1_5_id") REFERENCES "Mod_Fliesszeit_Result"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Mod_Fliesszeit" ADD CONSTRAINT "Mod_Fliesszeit_mod_fliesszeit_result_2_id_fkey" FOREIGN KEY ("mod_fliesszeit_result_2_id") REFERENCES "Mod_Fliesszeit_Result"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Mod_Fliesszeit" ADD CONSTRAINT "Mod_Fliesszeit_mod_fliesszeit_result_3_id_fkey" FOREIGN KEY ("mod_fliesszeit_result_3_id") REFERENCES "Mod_Fliesszeit_Result"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Mod_Fliesszeit" ADD CONSTRAINT "Mod_Fliesszeit_mod_fliesszeit_result_4_id_fkey" FOREIGN KEY ("mod_fliesszeit_result_4_id") REFERENCES "Mod_Fliesszeit_Result"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Koella" ADD CONSTRAINT "Koella_koella_result_1_5_id_fkey" FOREIGN KEY ("koella_result_1_5_id") REFERENCES "Koella_Result"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Koella" ADD CONSTRAINT "Koella_koella_result_2_id_fkey" FOREIGN KEY ("koella_result_2_id") REFERENCES "Koella_Result"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Koella" ADD CONSTRAINT "Koella_koella_result_3_id_fkey" FOREIGN KEY ("koella_result_3_id") REFERENCES "Koella_Result"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Koella" ADD CONSTRAINT "Koella_koella_result_4_id_fkey" FOREIGN KEY ("koella_result_4_id") REFERENCES "Koella_Result"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "ClarkWSL" ADD CONSTRAINT "ClarkWSL_clarkwsl_result_1_5_id_fkey" FOREIGN KEY ("clarkwsl_result_1_5_id") REFERENCES "ClarkWSL_Result"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "ClarkWSL" ADD CONSTRAINT "ClarkWSL_clarkwsl_result_2_id_fkey" FOREIGN KEY ("clarkwsl_result_2_id") REFERENCES "ClarkWSL_Result"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "ClarkWSL" ADD CONSTRAINT "ClarkWSL_clarkwsl_result_3_id_fkey" FOREIGN KEY ("clarkwsl_result_3_id") REFERENCES "ClarkWSL_Result"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "ClarkWSL" ADD CONSTRAINT "ClarkWSL_clarkwsl_result_4_id_fkey" FOREIGN KEY ("clarkwsl_result_4_id") REFERENCES "ClarkWSL_Result"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "NAM" ADD CONSTRAINT "NAM_nam_result_1_5_id_fkey" FOREIGN KEY ("nam_result_1_5_id") REFERENCES "NAM_Result"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "NAM" ADD CONSTRAINT "NAM_nam_result_2_id_fkey" FOREIGN KEY ("nam_result_2_id") REFERENCES "NAM_Result"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "NAM" ADD CONSTRAINT "NAM_nam_result_3_id_fkey" FOREIGN KEY ("nam_result_3_id") REFERENCES "NAM_Result"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "NAM" ADD CONSTRAINT "NAM_nam_result_4_id_fkey" FOREIGN KEY ("nam_result_4_id") REFERENCES "NAM_Result"("id") ON DELETE CASCADE ON UPDATE CASCADE;
