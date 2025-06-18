/*
  Warnings:

  - Added the required column `number` to the `Annualities` table without a default value. This is not possible if the table is not empty.

*/
-- AlterTable
ALTER TABLE "Annualities" ADD COLUMN     "number" DOUBLE PRECISION NOT NULL;

-- AlterTable
ALTER TABLE "Mod_Fliesszeit" ALTER COLUMN "TB_start" SET DEFAULT 30,
ALTER COLUMN "istep" SET DEFAULT 5,
ALTER COLUMN "tol" SET DEFAULT 5,
ALTER COLUMN "max_iter" SET DEFAULT 1000;
