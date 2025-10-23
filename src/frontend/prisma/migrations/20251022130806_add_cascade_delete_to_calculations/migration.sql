-- DropForeignKey
ALTER TABLE "ClarkWSL" DROP CONSTRAINT "ClarkWSL_project_id_fkey";

-- DropForeignKey
ALTER TABLE "Fractions" DROP CONSTRAINT "Fractions_clarkwsl_id_fkey";

-- DropForeignKey
ALTER TABLE "Koella" DROP CONSTRAINT "Koella_project_id_fkey";

-- DropForeignKey
ALTER TABLE "Mod_Fliesszeit" DROP CONSTRAINT "Mod_Fliesszeit_project_id_fkey";

-- DropForeignKey
ALTER TABLE "NAM" DROP CONSTRAINT "NAM_project_id_fkey";

-- AddForeignKey
ALTER TABLE "Mod_Fliesszeit" ADD CONSTRAINT "Mod_Fliesszeit_project_id_fkey" FOREIGN KEY ("project_id") REFERENCES "Project"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Koella" ADD CONSTRAINT "Koella_project_id_fkey" FOREIGN KEY ("project_id") REFERENCES "Project"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "ClarkWSL" ADD CONSTRAINT "ClarkWSL_project_id_fkey" FOREIGN KEY ("project_id") REFERENCES "Project"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Fractions" ADD CONSTRAINT "Fractions_clarkwsl_id_fkey" FOREIGN KEY ("clarkwsl_id") REFERENCES "ClarkWSL"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "NAM" ADD CONSTRAINT "NAM_project_id_fkey" FOREIGN KEY ("project_id") REFERENCES "Project"("id") ON DELETE CASCADE ON UPDATE CASCADE;
