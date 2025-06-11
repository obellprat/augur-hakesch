/*
  Warnings:

  - Changed the type of `rp_low` on the `IDF_Parameters` table. No cast exists, the column would be dropped and recreated, which cannot be done if there is data, since the column is required.
  - Changed the type of `rp_high` on the `IDF_Parameters` table. No cast exists, the column would be dropped and recreated, which cannot be done if there is data, since the column is required.

*/
-- AlterTable
ALTER TABLE "IDF_Parameters" DROP COLUMN "rp_low",
ADD COLUMN     "rp_low" DOUBLE PRECISION NOT NULL,
DROP COLUMN "rp_high",
ADD COLUMN     "rp_high" DOUBLE PRECISION NOT NULL;
