/*
  Warnings:

  - You are about to drop the column `mod_fliesszeit` on the `Mod_Fliesszeit_Result` table. All the data in the column will be lost.
  - A unique constraint covering the columns `[mod_fliesszeit_result_id]` on the table `Mod_Fliesszeit` will be added. If there are existing duplicate values, this will fail.

*/
-- DropForeignKey
ALTER TABLE "Mod_Fliesszeit_Result" DROP CONSTRAINT "Mod_Fliesszeit_Result_mod_fliesszeit_fkey";

-- DropIndex
DROP INDEX "Mod_Fliesszeit_Result_mod_fliesszeit_key";

-- AlterTable
ALTER TABLE "Mod_Fliesszeit" ADD COLUMN     "mod_fliesszeit_result_id" INTEGER;

-- AlterTable
ALTER TABLE "Mod_Fliesszeit_Result" DROP COLUMN "mod_fliesszeit";

-- CreateIndex
CREATE UNIQUE INDEX "Mod_Fliesszeit_mod_fliesszeit_result_id_key" ON "Mod_Fliesszeit"("mod_fliesszeit_result_id");

-- AddForeignKey
ALTER TABLE "Mod_Fliesszeit" ADD CONSTRAINT "Mod_Fliesszeit_mod_fliesszeit_result_id_fkey" FOREIGN KEY ("mod_fliesszeit_result_id") REFERENCES "Mod_Fliesszeit_Result"("id") ON DELETE CASCADE ON UPDATE CASCADE;
